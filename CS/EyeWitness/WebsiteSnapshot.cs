using System;
using System.Drawing;
using System.Threading;
using System.Windows.Forms;

namespace EyeWitness
{
    /// <summary>
    ///  Borrowed and edited from the genius people at https://github.com/AppReadyGo/EyeTracker
    ///  They don't have a license so just be aware of that
    /// </summary>
    
    public class WebsiteSnapshot
    {
        private string Url { get; set; }
        private int? BrowserWidth { get; set; }
        private int? BrowserHeight { get; set; }
        private Bitmap Bitmap { get; set; }

        public WebsiteSnapshot(string url, int? browserWidth = null, int? browserHeight = null)
        {
            Rectangle bounds = Screen.PrimaryScreen.Bounds;
            this.Url = url;

            if (browserHeight == null && browserWidth == null)
            {
                this.BrowserHeight = bounds.Height;
                this.BrowserWidth = bounds.Width;
            }
            else
            {
                this.BrowserWidth = browserWidth;
                this.BrowserHeight = browserHeight;
            }
        }

        public Bitmap GenerateWebSiteImage(int timeout = 30000)
        {
            Thread thread = new Thread(delegate()
            {
                _GenerateWebSiteImage();
            });
            thread.SetApartmentState(ApartmentState.STA);
            try
            {
                thread.Start();
                thread.Join(timeout);
            }
            catch (AccessViolationException)
            {
                thread.Abort();
            }
            
            
            return Bitmap;
        }

        private void _GenerateWebSiteImage()
        {
            CancellationToken ct = new CancellationToken();
            using (WebBrowser webBrowser = new WebBrowser { ScrollBarsEnabled = false, Visible = false })
            {
                webBrowser.Hide();
                webBrowser.ScriptErrorsSuppressed = true;
                webBrowser.ScrollBarsEnabled = false;
                try
                {
                    webBrowser.Navigate(Url, "_self");
                    webBrowser.DocumentCompleted += WebBrowserDocumentCompleted;
                    while (webBrowser.ReadyState != WebBrowserReadyState.Complete)
                    {
                        try
                        {
                            Application.DoEvents();
                            ct.ThrowIfCancellationRequested();
                        }
                        catch (Exception e)
                        {
                            Console.WriteLine(e);
                            throw;
                        }
                    }
                }

                catch (AccessViolationException)
                {
                    //just pass
                }

                finally
                {
                    if (!webBrowser.IsDisposed)
                        webBrowser.Dispose();
                }
            }
        }

        private void WebBrowserDocumentCompleted(object sender, WebBrowserDocumentCompletedEventArgs e)
        {
            WebBrowser webBrowser = sender as WebBrowser;
            if (!BrowserWidth.HasValue)
            {
                if (webBrowser != null && webBrowser.Document?.Body != null)
                    BrowserWidth = webBrowser.Document.Body.ScrollRectangle.Width + webBrowser.Margin.Horizontal;
            }

            if (!BrowserHeight.HasValue)
            {
                if (webBrowser != null && webBrowser.Document?.Body != null)
                    BrowserHeight = webBrowser.Document.Body.ScrollRectangle.Height + webBrowser.Margin.Vertical;
            }

            if (BrowserWidth != null)
                if (BrowserHeight != null)
                    if (webBrowser != null)
                        webBrowser.ClientSize = new Size(BrowserWidth.Value, BrowserHeight.Value);

            if (webBrowser != null)
            {
                Bitmap = new Bitmap(webBrowser.Bounds.Width, webBrowser.Bounds.Height);
                //webBrowser.BringToFront();
                webBrowser?.DrawToBitmap(Bitmap, webBrowser.Bounds);
            }
        }
    }
}