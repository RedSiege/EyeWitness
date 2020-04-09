using System;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Security;
using System.Threading;
using System.Windows.Forms;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Security;
using System.ComponentModel;
using System.Threading.Tasks;

namespace EyeWitness
{
    public class WitnessedServer
    {
        static string sourceCode = "";
        public string headers = "";
        public string sourcePath = "";
        public string headerPath = "";
        public string imgPath = "";
        public string imgPathInternal = "";
        public string urlSaveName = "";
        static string errorState = "";
        public string remoteSystem = "";
        public string webpageTitle = "";
        public string defaultCreds = null;
        public string systemCategory = "uncat";

        public void CheckCreds(Dictionary<string, string> catDict, Dictionary<string, string> sigDict)
        {
            int elementArrayInt = 0;

            // Check for the existence of a signature line within the source code
            foreach (KeyValuePair<string, string> entry in sigDict)
            {
                bool credGood = true;
                if (entry.Key.Contains(";"))
                {
                    string[] elementArray = entry.Key.Split(';');
                    elementArrayInt = elementArray.Length;
                    foreach (string singleElement in elementArray)
                    {
                        if (!(sourceCode.Contains(singleElement)))
                        {
                            credGood = false;
                        }
                    }
                    if (credGood)
                    {
                        defaultCreds += "<br><br><b> Potential Default Creds: </b>" + SecurityElement.Escape(sigDict[entry.Key]);
                    }
                }
                // If the line in signatures.txt only has one check (no simicolons)
                else
                {
                    if (sourceCode.Contains(entry.Key))
                    {
                        defaultCreds += "<br><br><b> Potential Default Creds: </b>" + SecurityElement.Escape(sigDict[entry.Key]);
                    }
                }
            }

            int catArrayElement = 0;
            foreach (KeyValuePair<string, string> entry in catDict)
            {
                bool catGood = true;
                if (entry.Key.Contains(";"))
                {
                    string[] elementArray = entry.Key.Split(';');
                    catArrayElement = elementArray.Length;
                    foreach (string singleElement in elementArray)
                    {
                        if (!(sourceCode.Contains(singleElement)))
                        {
                            catGood = false;
                        }
                    }
                    if (catGood)
                    {
                        systemCategory = catDict[entry.Key];
                    }
                }
                // If the line in signatures.txt only has one check (no simicolons)
                else
                {
                    if (sourceCode.Contains(entry.Key))
                    {
                        systemCategory = catDict[entry.Key];
                    }
                }
            }
            return;
        }

        private void DocumentCompleted(object sender, WebBrowserDocumentCompletedEventArgs e)
        {
            // Now that the page is loaded, save it to a bitmap
            WebBrowser browser = sender as WebBrowser;
            browser.Visible = false;
            try
            {
                // Get a Bitmap representation of the webpage as it's rendered in the WebBrowser control
                Rectangle bounds = Screen.PrimaryScreen.Bounds;
                using (Bitmap bitmap = new Bitmap(bounds.Width, bounds.Height))
                {
                    browser.DrawToBitmap(bitmap, bounds);
                    bitmap.Save(imgPathInternal);
                }
            }
            catch(ThreadAbortException)
            {
                Console.WriteLine("Error aborting thread, returning");
                browser.Dispose();
                return;
            }
            finally
            {
                browser.Dispose();
            }
        }

        void savePath()
        {
            //Save the URL as a variable
            string NameUrl = remoteSystem.Replace("/", ".");
            NameUrl = NameUrl.Replace(":", ".");
            if (NameUrl.EndsWith("/"))
            {
                urlSaveName = NameUrl.Remove(NameUrl.Length - 1, 1);
            }
            else
            {
                urlSaveName = NameUrl;
            }

            // Define the paths where everything will be saved
            sourcePath = Program.witnessDir + "\\src\\" + urlSaveName + ".txt";
            imgPath = Program.witnessDir + "\\images\\" + urlSaveName + ".bmp";
            imgPathInternal = imgPath;
            headerPath = Program.witnessDir + "\\headers\\" + urlSaveName + ".txt";
        }

        public void RunWithTimeout(TimeSpan timeout)
        {
            //Capture an image of the given URL within a thread
            //Console.WriteLine("Capturing " + remoteSystem);

            Thread workerThread = new Thread(delegate ()
            {
                try
                {
                    //Create bounds the same size as the screen
                    Rectangle bounds = Screen.PrimaryScreen.Bounds;

                    //Don't care about TLS issues
                    ServicePointManager.ServerCertificateValidationCallback = new RemoteCertificateValidationCallback
                    (
                        delegate { return true; }
                    );
                    using (WebBrowser br = new WebBrowser())
                    {
                        br.Width = bounds.Width;
                        br.Height = bounds.Height;
                        br.ScriptErrorsSuppressed = true;
                        br.ScrollBarsEnabled = false;

                        
                        br.Navigate(remoteSystem);
                          
                        br.Visible = false;
                        br.DocumentCompleted += new WebBrowserDocumentCompletedEventHandler(DocumentCompleted);
                        br.NewWindow += new System.ComponentModel.CancelEventHandler(WinFormBrowser_NewWindow);
                    

                    while (br.ReadyState != WebBrowserReadyState.Complete)
                        {
                            System.Windows.Forms.Application.DoEvents();
                            //Application.Run();
                        }                        
                    }
                }
                catch
                {
                    return;
                }
                
            });
            workerThread.SetApartmentState(ApartmentState.STA);
            workerThread.Start();

            bool finished = workerThread.Join(timeout);
            if (!finished)
                try
                {
                    workerThread.Abort();
                    Console.WriteLine("[-] Thread has been aborted for url: " + remoteSystem);
                }
                catch (ThreadAbortException)
                {
                    //Thread.ResetAbort();
                }
        }

        public async Task<String> RunWithTimeoutCancellation(CancellationToken cancellationToken)
        {
            //Capture an image of the given URL within a thread

            Thread workerThread = new Thread(delegate ()
            {
                try
                {
                    //Create bounds the same size as the screen
                    Rectangle bounds = Screen.PrimaryScreen.Bounds;

                    //Don't care about TLS issues
                    ServicePointManager.ServerCertificateValidationCallback = new RemoteCertificateValidationCallback
                    (
                        delegate { return true; }
                    );
                    using (WebBrowser br = new WebBrowser())
                    {
                        br.Width = bounds.Width;
                        br.Height = bounds.Height;
                        br.ScriptErrorsSuppressed = true;
                        br.ScrollBarsEnabled = false;


                        br.Navigate(remoteSystem);

                        br.Visible = false;
                        br.DocumentCompleted += new WebBrowserDocumentCompletedEventHandler(DocumentCompleted);
                        br.NewWindow += new System.ComponentModel.CancelEventHandler(WinFormBrowser_NewWindow);


                        while (br.ReadyState != WebBrowserReadyState.Complete)
                        {
                            System.Windows.Forms.Application.DoEvents();
                            //Application.Run();
                        }
                    }
                }
                catch
                {
                    return;
                }

            });
            workerThread.SetApartmentState(ApartmentState.STA);
            await Task.Run(() =>
            {
                workerThread.Start();
                bool finished = workerThread.Join(30000);
                if (!finished)
                    try
                    {
                        workerThread.Abort();
                        Console.WriteLine("[-] Thread has been aborted for url: " + remoteSystem);
                    }
                    catch (ThreadAbortException)
                    {
                        //Thread.ResetAbort();
                    }
            });
            return "finished";


        }

        void WinFormBrowser_NewWindow(object sender, System.ComponentModel.CancelEventArgs e)
        {
            WebBrowser browser = sender as WebBrowser;
            e.Cancel = true;
            Application.Exit();
            browser.Navigate(remoteSystem);
        }

        public async Task<String> SourcerAsync(CancellationToken cancellationToken)
        {

            // Capture source code and headers
            ServicePointManager.Expect100Continue = true;
            // fix for allowing tls12
            ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072;
            await Task.Run(async() =>
            {
                using (WebClient witnessClient = new WebClient())
                {
                    // Instantiate the CancellationTokenSource.
                    //var taskCompletionSource = new TaskCompletionSource<bool>();
                    //cts.CancelAfter(20000);

                    try
                    {
                        ServicePointManager.ServerCertificateValidationCallback = new RemoteCertificateValidationCallback
                            (
                                delegate { return true; }
                            );
                        // Uri test = Uri.Parse(remoteSystem);
                        sourceCode = witnessClient.DownloadString(remoteSystem);
                        headers = witnessClient.ResponseHeaders.ToString();
                        webpageTitle = Regex.Match(sourceCode, @"\<title\b[^>]*\>\s*(?<Title>[\s\S]*?)\</title\>",
                                       RegexOptions.IgnoreCase).Groups["Title"].Value;
                        File.WriteAllText(Program.witnessDir + "\\src\\" + urlSaveName + ".txt", sourceCode);
                        File.WriteAllText(Program.witnessDir + "\\headers\\" + urlSaveName + ".txt", headers);
                        witnessClient.Dispose();
                        return;
                    }

                    catch (Exception e)
                    {
                        //Console.WriteLine(e);
                        Console.WriteLine("[*] Offline Server - " + remoteSystem);
                        errorState = "offline";
                        systemCategory = "offline";
                        webpageTitle = "Server Offline";
                        headers = "Server Offline";
                        return;
                    }
                }
            }, cancellationToken);
            return "finished";
        }  

        public WitnessedServer(string systemTargeted)
        {
            remoteSystem = systemTargeted;
            savePath();
        }

        //We're not using htis now but keep it in just in case we need it for the future
        public static void SetFeatureBrowserEmulation()
        {
            try
            {
                using (var key = Microsoft.Win32.Registry.CurrentUser.OpenSubKey(
                        @"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION",
                        true))
                {
                    var app = System.IO.Path.GetFileName(Application.ExecutablePath);
                    key.SetValue(app, 11001, Microsoft.Win32.RegistryValueKind.DWord);
                    key.Close();
                }
            }
            catch
            {
                Console.WriteLine("Error in setting reg value to use latest IE");
            }
        }
    }
}
