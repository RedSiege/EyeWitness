using System;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Security;
using System.Threading.Tasks;
using Microsoft.Win32;

namespace EyeWitness
{
    public class WitnessedServer
    {
        private static string _sourceCode = "";
        public string headers = "";
        public string sourcePath = "";
        public string headerPath = "";
        public string imgPath = "";
        public string imgPathInternal = "";
        public string urlSaveName = "";
        static string errorState = "";
        public string remoteSystem;
        public string webpageTitle = "";
        public string defaultCreds;
        public string systemCategory = "uncat";

        public void CheckCreds(Dictionary<string, string> catDict, Dictionary<string, string> sigDict)
        {
            // Check for the existence of a signature line within the source code
            foreach (KeyValuePair<string, string> entry in sigDict)
            {
                bool credGood = true;
                if (entry.Key.Contains(";"))
                {
                    string[] elementArray = entry.Key.Split(';');
                    foreach (string singleElement in elementArray)
                    {
                        if (!_sourceCode.Contains(singleElement))
                            credGood = false;
                    }

                    if (credGood)
                        defaultCreds += "<br><br><b> Potential Default Creds: </b>" +
                                        SecurityElement.Escape(sigDict[entry.Key]);
                }
                // If the line in signatures.txt only has one check (no simicolons)
                else
                {
                    if (_sourceCode.Contains(entry.Key))
                        defaultCreds += "<br><br><b> Potential Default Creds: </b>" +
                                        SecurityElement.Escape(sigDict[entry.Key]);
                }
            }

            foreach (KeyValuePair<string, string> entry in catDict)
            {
                bool catGood = true;
                if (entry.Key.Contains(";"))
                {
                    string[] elementArray = entry.Key.Split(';');
                    foreach (string singleElement in elementArray)
                    {
                        if (!_sourceCode.Contains(singleElement))
                            catGood = false;
                    }

                    if (catGood)
                        systemCategory = catDict[entry.Key];
                }

                // If the line in signatures.txt only has one check (no simicolons)
                else
                {
                    if (_sourceCode.Contains(entry.Key))
                        systemCategory = catDict[entry.Key];
                }
            }
        }

        private void SavePath()
        {
            //Save the URL as a variable
            string nameUrl = remoteSystem.Replace("/", ".");
            nameUrl = nameUrl.Replace(":", ".");
            nameUrl = nameUrl.Replace("?", ".");
            nameUrl = nameUrl.Replace("&", ".");
            urlSaveName = nameUrl.EndsWith("/") ? nameUrl.Remove(nameUrl.Length - 1, 1) : nameUrl;

            // Define the paths where everything will be saved
            sourcePath = Program.witnessDir + "\\src\\" + urlSaveName + ".txt";
            imgPath = Program.witnessDir + "\\images\\" + urlSaveName + ".bmp";
            imgPathInternal = imgPath;
            headerPath = Program.witnessDir + "\\headers\\" + urlSaveName + ".txt";
        }

        public async Task<string> SourcerAsync(CancellationToken cancellationToken)
        {

            // Capture source code and headers
            ServicePointManager.Expect100Continue = true;
            // fix for allowing tls12
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            await Task.Run(async () =>
            {
                using (WebClient witnessClient = new WebClient())
                {
                    try
                    {
                        ServicePointManager.ServerCertificateValidationCallback = delegate { return true; };
                        // Uri test = Uri.Parse(remoteSystem);

                        cancellationToken.Register(witnessClient.CancelAsync);
                        _sourceCode = await witnessClient.DownloadStringTaskAsync(remoteSystem);
                        cancellationToken.ThrowIfCancellationRequested();
                        headers = witnessClient.ResponseHeaders.ToString();

                        webpageTitle = Regex.Match(_sourceCode, @"\<title\b[^>]*\>\s*(?<Title>[\s\S]*?)\</title\>",
                            RegexOptions.IgnoreCase).Groups["Title"].Value;
                        File.WriteAllText(Program.witnessDir + "\\src\\" + urlSaveName + ".txt", _sourceCode);
                        File.WriteAllText(Program.witnessDir + "\\headers\\" + urlSaveName + ".txt", headers);
                    }

                    catch (Exception e)
                    {
                        //Console.WriteLine(e);
                        Console.WriteLine($"[*] Offline Server - {remoteSystem} - {e.Message}");
                        errorState = "offline";
                        systemCategory = "offline";
                        webpageTitle = "Server Offline";
                        headers = "Server Offline";
                    }
                    finally
                    {
                        witnessClient.Dispose();
                    }
                }
            }, cancellationToken);
            return "finished";
        }

        public WitnessedServer(string systemTargeted)
        {
            remoteSystem = systemTargeted;
            SavePath();
        }

        //We're not using this now but keep it in just in case we need it for the future
        public static void SetFeatureBrowserEmulation()
        {
            try
            {
                using (RegistryKey key = Microsoft.Win32.Registry.CurrentUser.OpenSubKey(
                    @"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION",
                    true))
                {
                    var app = Path.GetFileName(Application.ExecutablePath);
                    key.SetValue(app, 11001, RegistryValueKind.DWord);
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
