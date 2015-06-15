import rdpy.core.log as log
import sys

try:
    from PyQt4 import QtGui
    from rdpy.protocol.rfb import rfb
    from rdpy.ui.qt4 import qtImageFormatFromRFBPixelFormat
except ImportError:
    print '[*] VNC Libraries not found.'
    print '[*] Please run the script in the setup directory!'
    sys.exit()


class RFBScreenShotFactory(rfb.ClientFactory):

    """
    @summary: Factory for screenshot exemple
    """
    __INSTANCE__ = 0

    def __init__(self, path, reactor, app, vnc_obj, dbm=None):
        """
        @param password: password for VNC authentication
        @param path: path of output screenshot
        """
        RFBScreenShotFactory.__INSTANCE__ += 1
        self._path = path
        self._password = ''
        self._reactor = reactor
        self._app = app
        self._dbm = dbm
        self._obj = vnc_obj

    def clientConnectionLost(self, connector, reason):
        """
        @summary: Connection lost event
        @param connector: twisted connector use for rfb connection (use reconnect to restart connection)
        @param reason: str use to advertise reason of lost connection
        """
        if not 'Connection was closed cleanly' in str(reason):
            self._dbm.open_connection()
            self._obj.error_state = True
            self._dbm.update_vnc_rdp_object(self._obj)
            self._dbm.close()

        RFBScreenShotFactory.__INSTANCE__ -= 1
        if(RFBScreenShotFactory.__INSTANCE__ == 0):
            try:
                self._reactor.stop()
            except:
                pass
            self._app.exit()

    def clientConnectionFailed(self, connector, reason):
        """
        @summary: Connection failed event
        @param connector: twisted connector use for rfb connection (use reconnect to restart connection)
        @param reason: str use to advertise reason of lost connection
        """
        if self._dbm:
            self._dbm.open_connection()
            self._obj.error_state = True
            self._dbm.update_vnc_rdp_object(self._obj)
            self._dbm.close()
        print '[*] Error connecting to {0}:{1}'.format(
            self._obj.remote_system, self._obj.port)
        RFBScreenShotFactory.__INSTANCE__ -= 1
        if(RFBScreenShotFactory.__INSTANCE__ == 0):
            try:
                self._reactor.stop()
            except:
                pass
            self._app.exit()

    def buildObserver(self, controller, addr):
        """
        @summary: build ScreenShot observer
        @param controller: RFBClientController
        @param addr: address of target
        """
        class ScreenShotObserver(rfb.RFBClientObserver):

            """
            @summary: observer that connect, cache every image received and save at deconnection
            """

            def __init__(self, controller, path, dbm, obj):
                """
                @param controller: RFBClientController
                @param path: path of output screenshot
                """
                rfb.RFBClientObserver.__init__(self, controller)
                self._path = path
                self._buffer = None
                self._dbm = dbm
                self._obj = obj
                self._complete = False
                print '[*] Connecting to {0}:{1} (VNC)'.format(
                    self._obj.remote_system, self._obj.port)

            def onUpdate(self, width, height, x, y, pixelFormat, encoding, data):
                """
                Implement RFBClientObserver interface
                @param width: width of new image
                @param height: height of new image
                @param x: x position of new image
                @param y: y position of new image
                @param pixelFormat: pixefFormat structure in rfb.message.PixelFormat
                @param encoding: encoding type rfb.message.Encoding
                @param data: image data in accordance with pixel format and encoding
                """
                imageFormat = qtImageFormatFromRFBPixelFormat(pixelFormat)
                if imageFormat is None:
                    if self._dbm:
                        self._dbm.open_connection()
                        self._obj.error_state = True
                        self._dbm.update_vnc_rdp_object(self._obj)
                        self._dbm.close()
                    log.error("Receive image in bad format")
                    return
                image = QtGui.QImage(data, width, height, imageFormat)

                with QtGui.QPainter(self._buffer) as qp:
                    qp.drawImage(x, y, image, 0, 0, width, height)
                    self._complete = True

                self._controller.close()

            def onReady(self):
                """
                @summary: callback use when RDP stack is connected (just before received bitmap)
                """
                width, height = self._controller.getScreen()
                self._buffer = QtGui.QImage(
                    width, height, QtGui.QImage.Format_RGB32)

            def onClose(self):
                """
                @summary: callback use when RDP stack is closed
                """
                if self._complete:
                    if self._dbm:
                        self._dbm.open_connection()
                        self._dbm.update_vnc_rdp_object(self._obj)
                        self._dbm.close()
                    self._buffer.save(self._path)

        controller.setPassword(self._password)
        return ScreenShotObserver(controller, self._path, self._dbm, self._obj)


def capture_host(cli_parsed, vnc_object):
    log._LOG_LEVEL = log.Level.ERROR
    app = QtGui.QApplication(sys.argv)

    # add qt4 reactor
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    reactor.connectTCP(
        vnc_object.remote_system, vnc_object.port, RFBScreenShotFactory(
            vnc_object.screenshot_path, reactor, app, vnc_object))

    reactor.runReturn()
    app.exec_()
