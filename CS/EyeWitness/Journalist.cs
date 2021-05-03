using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security;


namespace EyeWitness
{
    internal class Journalist
    {
        public string InitialReporter(int page, Dictionary<string, object[]> catDict, int totalPages)
        {
            string html = "";
            if (page == 0)
            {
                html += @"<html>
    <body>
    <center><h1>EyeWitness</h1></center>
    <center><html>
        <head>
        <title></title></head><br><br>";

                html += "<table cellpadding=\"10\" border=1><center>";

                foreach (KeyValuePair<string, object[]> entry in catDict)
                {
                    if((int)entry.Value.ElementAt(1) != 0)
                        html += "<tr><td style=\"padding: 5px;\">" + (string)entry.Value.ElementAt(0) + 
                                " </td><td style=\"padding: 5px;\"> " + (int)entry.Value.ElementAt(1) + "</td></tr>";
                }
                html += "<tr><td style =\"padding: 5px;\">" + "Total Pages Screenshotted" + "</td ><td style =\"padding: 5px;\">" + totalPages + "</td></tr>";

                html += @"</table>
                <br><br>

    ";
            }

            else
            {
                html += @"<html>
        <body>
        <center>
        ";
            }

            html += "<link rel=\"stylesheet\" href=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css\" type=\"text/css\"/><br>";
            html += "<center>Report generated on " + DateTime.Now.ToString("MM-dd-yy @ HH:mm:ss") + "</center>\n";
            html += "<center>" + BuildPages(totalPages) + "</center>\n";

            return html;
        }

        public string Reporter(WitnessedServer incomingServer)
        {
            string tempHtmlOutput = "";
            tempHtmlOutput += "<td><div style=\"display: inline-block; width: 300px; word-wrap: break-word\">";
            tempHtmlOutput += "<a href=\"" + incomingServer.remoteSystem + "\" target=\"_blank\">" + incomingServer.remoteSystem + "</a>\n<br><br>";
            tempHtmlOutput += "<br><b>Page Title: </b>" + incomingServer.webpageTitle + "<br>\n\n";
            tempHtmlOutput += "<br><b>Headers: </b>\n\n";

            // Split the header string into lines and make the variable bold
            foreach (string line in incomingServer.headers.Split(new[] { Environment.NewLine }, StringSplitOptions.None))
            {
                if (line.Contains(":"))
                {
                    string[] element = line.Split(new[] { ':' }, 2, StringSplitOptions.None);
                    //Escape any bad chars passed as a header
                    tempHtmlOutput += "<br> <b>" + SecurityElement.Escape(element[0]) + "</b>: " + SecurityElement.Escape(element[1]);
                }
            }

            if (incomingServer.defaultCreds != null)
            {
                tempHtmlOutput += "<br>" + incomingServer.defaultCreds;
            }

            tempHtmlOutput += "<br><br> <a href=\"src\\" + incomingServer.urlSaveName + ".txt\" ";
            tempHtmlOutput += "target=\"_blank\">Source Code</a></div></td><br>\n";
            tempHtmlOutput += "<td><div id=\"screenshot\"><a href=\"images\\" + incomingServer.urlSaveName + ".bmp\" ";
            tempHtmlOutput += "target=\"_blank\"><img src=\"images\\" + incomingServer.urlSaveName + ".bmp\" ";
            tempHtmlOutput += "height=\"400\"></a></div></td></tr><tr>\n\n";

            return tempHtmlOutput;
        }

        public string CategorizeInitial(string category, WitnessedServer incomingServer)
        {
            string tempHtmlOutput = "";

            if (incomingServer.systemCategory != null)
            {
                tempHtmlOutput += "<table><div align=\"left\"><tr><th><h2>" + category + "</h2></tr></th></div>";
                tempHtmlOutput += "<table border=\"1\">";
                tempHtmlOutput += @"
            <tr>
            <th>Web Request Info</th>
            <th>Web Screenshot</th></tr>
            <tr>";
            }

            return tempHtmlOutput;
        }

        public void FinalReporter(string html, int pageNumber, int pageNumbersTotal, string witnessDir)
        {
            //string html = "";

            html += "</table><br>"; //close out the category table and the screenshot/source table
            
            if (pageNumber != 0)
                html += BuildPages(pageNumbersTotal);

            File.WriteAllText(witnessDir + "\\report_page" + pageNumber + ".html", html);
        }

        public string BuildPages(int totalPageNumbers)
        {
            string htmlForPages = "";
            int pageNumbers = (int)Math.Ceiling((double)totalPageNumbers / 25);

            htmlForPages += "<center><br><a href=\"report_page1.html\">Page 1</a>";
            
            for (int page = 2; page <= pageNumbers; page++)
                htmlForPages += " <a href=\"report_page" + page + ".html\">Page " + page + "</a> ";
           
            htmlForPages += "\n<br><br></center></body><html>";
            return htmlForPages;
        }
    }
}
