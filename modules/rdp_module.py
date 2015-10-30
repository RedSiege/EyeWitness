import sys

try:
    import rdpy.core.log as log

    from PyQt4 import QtGui
    from rdpy.protocol.rdp import rdp
    from rdpy.ui.qt4 import RDPBitmapToQtImage
    from rdpy.core.error import RDPSecurityNegoFail
except ImportError:
    print '[*] RDP libraries not found.'
    print '[*] Please run the script in the setup directory!'
    sys.exit()

# set log level
log._LOG_LEVEL = log.Level.INFO


class RDPScreenShotFactory(rdp.ClientFactory):

    """
    @summary: Factory for screenshot exemple
    """
    __INSTANCE__ = 0
    __STATE__ = []

    def __init__(self, reactor, app, width, height, path, timeout, rdp_obj, dbm=None):
        """
        @param reactor: twisted reactor
        @param width: {integer} width of screen
        @param height: {integer} height of screen
        @param path: {str} path of output screenshot
        @param timeout: {float} close connection after timeout s without any updating
        """
        RDPScreenShotFactory.__INSTANCE__ += 1
        self._reactor = reactor
        self._app = app
        self._width = width
        self._height = height
        self._path = path
        self._timeout = timeout
        self._object = rdp_obj
        # NLA server can't be screenshooting
        self._security = rdp.SecurityLevel.RDP_LEVEL_SSL
        self._dbm = dbm

    def clientConnectionLost(self, connector, reason):
        """
        @summary: Connection lost event
        @param connector: twisted connector use for rdp connection (use reconnect to restart connection)
        @param reason: str use to advertise reason of lost connection
        """
        if reason.type == RDPSecurityNegoFail and self._security != "rdp":
            log.info("due to RDPSecurityNegoFail try standard security layer")
            self._security = rdp.SecurityLevel.RDP_LEVEL_RDP
            connector.connect()
            return
        RDPScreenShotFactory.__STATE__.append(
            (connector.host, connector.port, reason))
        RDPScreenShotFactory.__INSTANCE__ -= 1
        if(RDPScreenShotFactory.__INSTANCE__ == 0):
            try:
                self._reactor.stop()
            except:
                pass
            self._app.exit()

    def clientConnectionFailed(self, connector, reason):
        """
        @summary: Connection failed event
        @param connector: twisted connector use for rdp connection (use reconnect to restart connection)
        @param reason: str use to advertise reason of lost connection
        """
        log.info("connection failed : %s" % reason)
        if self._dbm:
            self._dbm.open_connection()
            self._object.error_state = True
            self._dbm.update_vnc_rdp_object(self._object)
            self._dbm.close()
        print '[*] Error connecting to {0}'.format(self._object.remote_system)
        RDPScreenShotFactory.__STATE__.append(
            (connector.host, connector.port, reason))
        RDPScreenShotFactory.__INSTANCE__ -= 1
        if(RDPScreenShotFactory.__INSTANCE__ == 0):
            try:
                self._reactor.stop()
            except:
                pass
            self._app.exit()

    def buildObserver(self, controller, addr):
        """
        @summary: build ScreenShot observer
        @param controller: RDPClientController
        @param addr: address of target
        """
        class ScreenShotObserver(rdp.RDPClientObserver):

            """
            @summary: observer that connect, cache every image received and save at deconnection
            """

            def __init__(self, controller, width, height, path, timeout, reactor, dbm, obj):
                """
                @param controller: {RDPClientController}
                @param width: {integer} width of screen
                @param height: {integer} height of screen
                @param path: {str} path of output screenshot
                @param timeout: {float} close connection after timeout s without any updating
                @param reactor: twisted reactor
                """
                rdp.RDPClientObserver.__init__(self, controller)
                self._buffer = QtGui.QImage(
                    width, height, QtGui.QImage.Format_RGB32)
                self._path = path
                self._timeout = timeout
                self._startTimeout = False
                self._reactor = reactor
                self._dbm = dbm
                self._obj = obj
                self._complete = False
                print '[*] Connecting to {0} (RDP)'.format(self._obj.remote_system)

            def onUpdate(self, destLeft, destTop, destRight, destBottom, width, height, bitsPerPixel, isCompress, data):
                """
                @summary: callback use when bitmap is received
                """
                image = RDPBitmapToQtImage(
                    width, height, bitsPerPixel, isCompress, data)
                with QtGui.QPainter(self._buffer) as qp:
                    # draw image
                    qp.drawImage(
                        destLeft, destTop, image, 0, 0, destRight - destLeft + 1, destBottom - destTop + 1)
                    self._complete = True
                if not self._startTimeout:
                    self._startTimeout = False
                    self._reactor.callLater(self._timeout, self.checkUpdate)

            def onReady(self):
                """
                @summary: callback use when RDP stack is connected (just before received bitmap)
                """
                log.info("connected %s" % addr)

            def onSessionReady(self):
                """
                @summary: Windows session is ready
                @see: rdp.RDPClientObserver.onSessionReady
                """
                pass

            def onClose(self):
                """
                @summary: callback use when RDP stack is closed
                """
                log.info("save screenshot into %s" % self._path)
                if self._complete:
                    if self._dbm:
                        self._dbm.open_connection()
                        self._dbm.update_vnc_rdp_object(self._obj)
                        self._dbm.close()
                    self._buffer.save(self._path)

            def checkUpdate(self):
                self._controller.close()

        controller.setScreen(self._width, self._height)
        controller.setSecurityLevel(self._security)
        return ScreenShotObserver(controller, self._width, self._height,
                                  self._path, self._timeout, self._reactor,
                                  self._dbm, self._object)


def capture_host(cli_parsed, rdp_object):
    log._LOG_LEVEL = log.Level.ERROR
    width = 1200
    height = 800
    timeout = cli_parsed.timeout

    app = QtGui.QApplication(sys.argv)

    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor

    reactor.connectTCP(
        rdp_object.remote_system, int(rdp_object.port), RDPScreenShotFactory(
            reactor, app, width, height,
            rdp_object.screenshot_path, timeout, rdp_object))

    reactor.runReturn()
    app.exec_()
