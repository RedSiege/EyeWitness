#!/usr/bin/env ruby

# This is a port of EyeWitness to Ruby, using a new screenshot engine

require 'cgi'
require 'ipaddr'
require 'net/http'
require 'net/https'
require 'netaddr'
require 'nokogiri'
require 'optparse'
require 'ostruct'
require 'pp'
require 'selenium-webdriver'
require 'socket'
require 'timeout'
require 'uri'


class CliParser

  def self.parse(args)

    # Used for a hash-like data structure
    options = OpenStruct.new

    # Set the default values
    options.file_name = nil
    options.nessus_xml = nil
    options.nmap_xml = nil
    options.single_website = nil
    options.create_targets = nil
    options.timeout = 7
    options.jitter = nil
    options.dir_name = "none"
    options.results_number = 25
    options.ua_name = nil
    options.cycle = "none"
    options.difference = 50
    options.skip_creds = false
    options.localscan = nil
    options.rid_dns = false

    opt_parser = OptionParser.new do |opts|
      opts.banner = "Usage: [options]"

      # Grouped for EyeWitness Input functions
      opts.on("-f", "--filename file.txt", "File containing URLs to screenshot") do |in_filename|
        options.file_name = in_filename
      end
      opts.on("--nessus file.nessus", "Nessus .nessus file output") do |nessus_xml|
        options.nessus_xml = nessus_xml
      end
      opts.on("--nmap file.xml", "Nmap XML file output") do |nmap_xml|
        options.nmap_xml = nmap_xml
      end
      opts.on("-s", "--single URL", "Single URL to screenshot") do |single_url|
        options.single_website = single_url
      end
      opts.on("--no-dns", "Parse nmap XML and only use IP address,",
          "instead of DNS for web server") do |rid_dns|
        options.rid_dns = true
      end
      opts.on("--createtargets Filename", "Create a file containing web servers",
          "from nmap or nessus output.\n\n") do |target_make|
        options.create_targets = target_make
      end

      # Timing options
      opts.on("-t", "--timeout 7", Integer, "Maximum number of seconds to wait while",
          "requesting a web page.") do |max_timeout|
        options.timeout = max_timeout
      end
      opts.on("--jitter 15", Integer, "Number of seconds to use as a base to",
          "randomly deviate from when making requests.\n\n") do |jit_num|
        opts.jitter = jit_num
      end

      # Report output options
      opts.on("-d Directory Name", "Name of directory for EyeWitness report.") do |d_name|
        options.dir_name = d_name
      end
      opts.on("--results 25", Integer, "Number of URLs displayed per page within",
          "the EyeWitness report.\n\n") do |res_num|
        options.results_number = res_num
      end

      # Useragent Options
      opts.on("--useragent Mozilla/4.0", "User agent to use when requesting all",
          "websites with EyeWitness.") do |ua_string|
        options.ua_name = ua_string
      end
      opts.on("--cycle All", "User agent \"group\" to cycle through when",
          "requesting web pages with EyeWitness.", "Browser, Mobile, Crawler, Scanner,", "Misc, All")\
          do |ua_cycle|
        options.cycle = ua_cycle
      end
      opts.on("--difference 50", Integer, "Difference threshold to use when comparing",
          "baseline request with modified user", "agent request.\n\n") do |diff_value|
        options.difference = diff_value
      end

      # Credential Check Options
      opts.on("--skipcreds", "Skip checking for default credentials.\n\n") do
        options.skip_creds = true
      end

      # Local Scanning Options
      opts.on("--localscan 192.168.1.0/24", "CIDR notation of IP range to scan.\n\n")\
          do |scan_range|
        options.localscan = scan_range
      end

      # Show help and command line flags
      opts.on_tail('-h', '--help', 'Show this message') do
        puts opts
        exit
      end

    end # end of opt_parser
    opt_parser.parse!(args)
    options
  end # End of self.parse
end # End cli_parser class


class NessusParser < Nokogiri::XML::SAX::Document
  
  def initialize
    @system_name = nil
    @port_number = nil
    @service_name = nil
    @plugin_name = nil
    @get_text = false
    @web_services = ['www', 'http?', 'https?']
    @url_list = []
  end

  def start_element name, attrs = []
    @attrs = attrs

    # Get the IP or name of the system scanned
    if name == "ReportHost"
      @attrs.each do |key, value|
        if key == "name"
          @system_name = value
        end
      end
    end

    # Grab the port number, service name, and plugin name
    if name == "ReportItem"
      @attrs.each do |key, value|
        if key == "port"
          @port_number = value
        end

        if key == "svc_name"
          @service_name = value
        end

        if key == "pluginName"
          value = value.downcase
          @web_services.each do |web_svc|
            if (@service_name.include? web_svc and value.include? "service detection")
              @plugin_name = value
            else
              @get_plug_out = false
            end
          end
        end
      end   # End of Report Items iterator
    end   # End of Report Item If statement

    if name == "plugin_output"
      if !@plugin_name.nil?
        @get_text = true
      end
    end
  end    # End of start_element function

  def characters string
    if @get_text and !string.empty?
      @plugin_output = string.gsub('\n', '')
      @get_text = false
    end
  end   # End of characters function


  def end_element name

    if (name == "plugin_output" and !@plugin_output.nil?)
      if (@plugin_output.include? 'TLS' or @plugin_output.include? 'SSL')
        @final_url = "https://#{@system_name}:#{@port_number}"
        if !@url_list.include? @final_url
          @url_list << @final_url
        end
      else
        @final_url = "http://#{@system_name}:#{@port_number}"
        if !@url_list.include? @final_url
          @url_list << @final_url
        end
      end
    end

    if name == "ReportItem"
      @plugin_output = nil
      @port_number = nil
      @service_name = nil
      @plugin_name = nil
      @get_text = false
    end

    if name == "ReportHost"
      @system_name = nil
    end
  end   # End of end_element function


  def url_get()
    return @url_list
  end
end   # End of nessus parsing class


class NmapParser < Nokogiri::XML::SAX::Document
  
  def initialize
    @ip_address = nil
    @hostname = nil
    @potential_port = nil
    @final_port_number = nil
    @port_state = nil
    @protocol = nil
    @tunnel = nil
    @final_url = nil
    @url_array = []
  end

  def ip_only()
    @nodns = true
  end

  def start_element name, attrs = []
    @attrs = attrs

    # Find IP addresses of all machines
    if name == "address"
      @attrs.each do |key, value|
        if key == "addr"
          @ip_address = value
        end
      end
    end

    if name == "hostname"
      @hostname = nil
      @attrs.each do |key, value|
        if key == "name"
          @hostname = value
        end
      end
    end
    
    if name == "port"
      @attrs.each do |key, value|
        if key == "portid"
          @potential_port = value
        end
      end
    end

    # Find port state
    if name == "state"
      @attrs.each do |key, value|
        if key == "state"
          if value == "open"
            @port_state = "open"
          else
            @port_state = "closed"
          end
        end
      end
    end

    # Find port "name"
    if name == "service"
      @attrs.each do |key, value|
        if key == "name"
          if value.include? "https"
            @protocol = "https://"
            @final_port_number = @potential_port

          elsif value.include? "http"
            @protocol = "http://"
            @final_port_number = @potential_port
          end
        end

        if key == "tunnel"
          if value.include? "ssl"
            @tunnel = "ssl"
          end
        end
      end   # end attrs iterator

      if @protocol == "https://" || @tunnel == "ssl"
        @protocol = "https://"
        if @hostname.nil? && @port_state == "open" || @nodns == true
          @final_url = "#{@protocol}#{@ip_address}:#{@final_port_number}"
          if !@url_array.include? @final_url
            @url_array << @final_url
          else
          end
          
        elsif @port_state == "open"
          @final_url = "#{@protocol}#{@hostname}:#{@final_port_number}"
          if !@url_array.include? @final_url
            @url_array << @final_url
          else
            @final_url = "#{@protocol}#{@ip_address}:#{@final_port_number}"
            if !@url_array.include? @final_url
            @url_array << @final_url
            else
            end
          end
        else
        end

      elsif @protocol == "http://"
        if @hostname.nil? && @port_state == "open" || @nodns == true
          @final_url = "#{@protocol}#{@ip_address}:#{@final_port_number}"
          if !@url_array.include? @final_url
            @url_array << @final_url
          else
          end
        elsif @port_state == "open"
          @final_url = "#{@protocol}#{@hostname}:#{@final_port_number}"
          if !@url_array.include? @final_url
            @url_array << @final_url
          else
            @final_url = "#{@protocol}#{@ip_address}:#{@final_port_number}"
            if !@url_array.include? @final_url
            @url_array << @final_url
            else
            end
          end
        else
        end   #End of if statement printing valid servers
      end    # End if statement looking at protocol and tunnel
    end    # End of if statement for the element starting with the name "service"
  end    # End of start_element function


  def end_element name
    if name == "host"
      @ip_address = nil
      @hostname = nil
    end

    if name == "service"
      @potential_port = nil
      @final_port_number = nil
      @port_state = nil
      @protocol = nil
      @tunnel = nil
      @final_url = nil
    end
  end   # End of end_element function


  def url_get()
    return @url_array
  end
end   # End of nmap parsing class


def capture_screenshot(sel_driver, output_path, url_to_grab)
  # Function used to capture screenshots with selenium
  sel_driver.navigate.to url_to_grab
  screenshot_name = url_to_grab.gsub(':', '').gsub('//', '.').gsub('/', '.')
  sourcecode_name = "#{screenshot_name}.txt"
  screenshot_name = "#{screenshot_name}.png"
  screen_cap_path = File.join(output_path, 'screens', screenshot_name)
  source_code_path = File.join(output_path, 'source', sourcecode_name)
  sel_driver.save_screenshot(screen_cap_path)
  File.open("#{source_code_path}", 'w') do |write_sourcecode|
    write_sourcecode.write(sel_driver.page_source)
  end

  return sel_driver.page_source
end

def default_creds(page_content, full_file_path)

  # This function parses the signatures file, and compares it with the source code
  # of the site connected to, and determines if there is a match
  creds_path = File.join("#{full_file_path}", "signatures.txt")

  begin
    File.open("#{creds_path}", "r") do |signature_file|
      signature_file.each_line do |signature|
        signature_delimeted = signature.split('|')[0]
        default_creds = signature.split('|')[1]

        # Values for signatures not found
        all_signatures = signature_delimeted.split(';')
        page_content = page_content.downcase
        signature_not_present = false

        all_signatures.each do |individual_signature|
          individual_signature = individual_signature.downcase
          if !page_content.include? "#{individual_signature}"
            signature_not_present = true
          end
        end

        if signature_not_present
        else
          return default_creds
        end
      end
    end

  rescue Errno::ENOENT
    puts "[*] WARNING Default credentials file not in same directory as EyeWitness!"
    puts "[*] Skipping credential check..."
  end  # End try catch

  return nil
end  #End of default creds function


def file_names(url_given)

  # Create the names of the screenshot and source code file used in the report
  url_given.gsub('\n', '')
  pic_name = url_given
  source_name = url_given
  source_name = source_name.gsub('://', '.').gsub('/', '.').gsub(':', '.')
  pic_name = "#{source_name}.png"
  source_name = "#{source_name}.txt"

  return url_given, source_name, pic_name
end  # End of file_names function


def folder_out(dir_name, full_path)

    # Create the CSS file for the report, and remove the extra 4 spaces
    css_file = 'img {
    max-width: 100%;
    height: auto;
    }
    #screenshot{
    overflow: auto;
    max-width: 850px;
    max-height: 550px;
    }'.gsub('    ', '')

    # Check to see if the directory name is null or not
    if dir_name == "none"
        # Get the Time and Date for creating the folder structure
        date_time = Time.new
        current_date = "#{date_time.month}#{date_time.day}#{date_time.year}"
        current_time = "#{date_time.hour}#{date_time.min}#{date_time.sec}"
        output_folder_name = "#{current_date}_#{current_time}"
    else
        output_folder_name = dir_name
    end

    output_folder_name = File.join(output_folder_name)

    # Check to see if output folder starts with C:\ or /
    if (output_folder_name.start_with?("C:\\") or output_folder_name.start_with?("/"))
        # Create the paths for making the directories (valid for Win and nix)
        source_out_folder_name = File.join("#{output_folder_name}", "source")
        screen_out_folder_name = File.join("#{output_folder_name}", "screens")
    else
        output_folder_name = File.join(full_path, output_folder_name)
        source_out_folder_name = File.join("#{output_folder_name}", "source")
        screen_out_folder_name = File.join("#{output_folder_name}", "screens")
    end

    # Actually create the directories now
    Dir.mkdir(output_folder_name)
    Dir.mkdir(source_out_folder_name)
    Dir.mkdir(screen_out_folder_name)

    # Write the css file out
    File.open("#{output_folder_name}/style.css", 'w') do |stylesheet|
        stylesheet.puts css_file
    end

    return output_folder_name, current_date, current_time
end # End of folder_out function


def html_encode(dangerous_data)
  # html encode data so we can't execute malicious scripts
  encoded = CGI::escapeHTML(dangerous_data)
  return encoded
end


def logistics(url_file)

  # This is basically a single function designed to parse a text file
  # and verify that each url starts with http or https
  file_urls = []
  num_urls = 0

  begin
    File.open(url_file, "r").each do |url|
      url = url.strip
      if !url.start_with?('http://') && !url.start_with?('https://')
        url = "http://#{url}"
      end
      file_urls << url
      num_urls += 1
    end
  rescue Errno::ENOENT
    puts "[*] Error: File not valid, or not found."
    puts "[*] Error: Please rerun and provide a valid file!"
    abort
  end

  return file_urls, num_urls
end  # End of logistics function


def request_comparison(original_content, new_content, max_difference)

  # compares the two requests and determines if it is above the "threshold"
  original_request_length = original_content.length
  new_request_length = new_content.length

  if new_request_length > original_request_length
    a, b = new_request_length, orig_request_length
    total_difference = a - b 
    if total_difference > max_difference
      return false, total_difference
    else
      return true, nil
    end

  else
    total_difference = orig_request_length - new_request_length
    if total_difference > max_difference
      return False, total_difference
    else
      return True, "None"
    end
  end   # End of if statement determing size of requests and performing math
end   # end of request comparison function


def scanner(cidr_range, tool_path)

  # Used to port scan a provided cidr range
  ports = [80, 443, 8080, 8443]

  # Live webservers
  live_webservers = []

  # port scanning code taken from
  # http://stackoverflow.com/questions/517219/ruby-see-if-a-port-is-open
  port_open = false

  # Create scanner output path
  scanner_output_path = File.join("#{tool_path}", "scanneroutput.txt")

  net1 = NetAddr::CIDR.create(cidr_range)

  net1.enumerate.each do |scan_ip|
    ports.each do |scan_port|
      begin
        Timeout.timeout(5) do
          begin
            s = TCPSocket.new(scan_ip, scan_port)
            s.close
            # Determine if we need to put http or https in front based off of port number
            if scan_port == 443 or scan_port == 8443
              live_webservers << "https://#{scan_ip}:#{scan_port}"
              puts "[*] #{scan_ip} looks to be listening on #{scan_port}."
            else
              live_webservers << "http://#{scan_ip}:#{scan_port}"
              puts "[*] #{scan_ip} looks to be listening on #{scan_port}."
            end
          rescue Errno::ECONNREFUSED, Errno::EHOSTUNREACH
          end
        end
      rescue Timeout::Error
      end
    end   # End port iterator
  end   # End of ip iterator

  server_out_file = File.join(tool_path, "scanneroutput.txt")

  File.open(server_out_file, 'w') do |srv_out|
    live_webservers.each do |web_srv|
      srv_out.write("#{web_srv}\n")
    end
  end
end   # End of scanner function


def selenium_driver()
  # Other drivers are available as well 
  #http://selenium.googlecode.com/svn/trunk/docs/api/rb/Selenium/WebDriver.html#for-class_method
  driver = Selenium::WebDriver.for :firefox
  return driver
end


def single_page_report(report_source, full_report_path)
  # The end of the html for a single paged report
  report_source += "</table>\n</body>\n</html>"

  report_file = File.join(full_report_path, "report.html")

  File.open(report_file, 'w') do |report_done|
    report_done.write(report_source)
  end
end   # End single page report function


def source_header_grab(url_to_head)

  # All of this code basically grabs the server headers and source code of the
  # provided URL
  uri = URI.parse("#{url_to_head}")
  
  if url_to_head.start_with?("http://")
    # code came from - http://www.rubyinside.com/nethttp-cheat-sheet-2940.html
    http = Net::HTTP.new(uri.host, uri.port)
    request = Net::HTTP::Get.new(uri.request_uri)
  elsif url_to_head.start_with?("https://")
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = true
    request = Net::HTTP::Get.new(uri.request_uri)
  else
    puts "[*] Error: Error with URL, please investigate!"
    exit
  end # end if statement for starting with http:// or https://

  # actually make the request
  response = http.request(request)

  # Return the response object
  # response.each gives header info
  return response
end   # End header_grab function


def table_maker(web_report_html, website_url, possible_creds, page_header_source, source_code_name,
  screenshot_name, length_difference, iwitness_dir, output_report_path)

  web_report_html += "<tr>\n<td><div style=\"display: inline-block; width: 300px; word-wrap:break-word\">\n"
  web_report_html += "<a href=\"#{website_url}\" target=\"_blank\">#{website_url}</a><br>"

  if !possible_creds.nil?
    encoded_creds = html_encode(possible_creds)
    web_report_html += "<br><b>Default credentials:</b> #{encoded_creds} <br>"
  end

  full_source_path = File.join(output_report_path, "source", source_code_name)

  page_header_source.each_header do |header, value|
    encoded_header = html_encode(header)
    encoded_value = html_encode(value)
    web_report_html += "<br><b>#{encoded_header}:</b> #{encoded_value}"
  end

  web_report_html += "<br><br><a href=\"source/#{source_code_name}\"target=\"_blank\">Source Code</a></div></td>\n
    <td><div id=\"screenshot\" style=\"display: inline-block; width:850px; height 400px; overflow: scroll;\">
    <a href=\"screens/#{screenshot_name}\" target=\"_blank\"><img src=\"screens/#{screenshot_name}\"
    height=\"400\"></a></div></td></tr>".gsub('    ', '')

  return web_report_html
end   # End table maker function


def title_screen()
  system("clear")
  puts "#############################################################################"
  puts "#                               EyeWitness                                  #"
  puts "#############################################################################\n\n"
  return
end # end of title_screen function


def user_agent_definition(cycle_value)
  # Create the dicts which hold different user agents.
  # Thanks to Chris John Riley for having an awesome tool which I could
  # get this info from.  His tool - UAtester.py -
  # http://blog.c22.cc/toolsscripts/ua-tester/
  # Additional user agent strings came from -
  # http://www.useragentstring.com/pages/useragentstring.php

  # "Normal" desktop user agents
  desktop_uagents = {
    "MSIE9.0" => "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1;Trident/5.0)",
    "MSIE8.0" => "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0)",
    "MSIE7.0" => "Mozilla/5.0 (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)",
    "MSIE6.0" => "Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)",
    "Chrome32.0.1667.0" => "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36",
    "Chrome31.0.1650.16" => "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36(KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36",
    "Firefox25" => "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0)Gecko/20100101 Firefox/25.0",
    "Firefox24" => "Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0,",
    "Opera12.14" => "Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14",
    "Opera12" => "Opera/12.0(Windows NT 5.1;U;en)Presto/22.9.168 Version/12.00",
    "Safari5.1.7" => "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2",
    "Safari5.0" => "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533.18.1 (KHTML, like Gecko) Version/5.0 Safari/533.16"
  }

  # Miscellaneous user agents
  misc_uagents = {
    "wget1.9.1" => "Wget/1.9.1",
    "curl7.9.8" => "curl/7.9.8 (i686-pc-linux-gnu) libcurl 7.9.8 (OpenSSL 0.9.6b) (ipv6 enabled)",
    "PyCurl7.23.1" => "PycURL/7.23.1",
    "Pythonurllib3.1" => "Python-urllib/3.1"
  }

  # Bot crawler user agents
  crawler_uagents = {
    "Baiduspider" => "Baiduspider+(+http://www.baidu.com/search/spider.htm)",
    "Bingbot" => "Mozilla/5.0 (compatible; bingbot/2.0 +http://www.bing.com/bingbot.htm)",
    "Googlebot2.1" => "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
    "MSNBot2.1" => "msnbot/2.1",
    "YahooSlurp!" => "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)"
  }

  # Random mobile User agents
  mobile_uagents = {
    "BlackBerry" => "Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.346 Mobile Safari/534.11+",
    "Android" => "Mozilla/5.0 (Linux; U; Android 2.3.5; en-us; HTC Vision Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "IEMobile9.0" => "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0)",
    "OperaMobile12.02" => "Opera/12.02 (Android 4.1; Linux; Opera Mobi/ADR-1111101157; U; en-US) Presto/2.9.201 Version/12.02",
    "iPadSafari6.0" => "Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d Safari/8536.25",
    "iPhoneSafari7.0.6" => "Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_6 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B651 Safari/9537.53"
  }

  # Web App Vuln Scanning user agents (give me more if you have any)
  scanner_uagents = {
      "w3af" => "w3af.org",
      "skipfish" => "Mozilla/5.0 SF/2.10b",
      "HTTrack" => "Mozilla/4.5 (compatible; HTTrack 3.0x; Windows 98)",
      "nikto" => "Mozilla/5.00 (Nikto/2.1.5) (Evasions:None) (Test:map_codes)"
  }

  # Combine all user agents into a single dictionary
  all_combined_uagents = desktop_uagents.merge(misc_uagents).merge(crawler_uagents).merge(mobile_uagents).merge(scanner_uagents)

  cycle_value = cycle_value.downcase

  if cycle_value == "browser"
    return desktop_uagents
  elsif cycle_value == "misc"
    return misc_uagents
  elsif cycle_value == "crawler"
    return crawler_uagents
  elsif cycle_value == "mobile"
    return mobile_uagents
  elsif cycle_value == "scanner"
    return scanner_uagents
  elsif cycle_value == "all"
    return all_combined_uagents
  else
    puts "[*] Error: You did not provide the type of user agents to cycle through!"
    puts "[*] Error: Defaulting to desktop browser user agents."
    return desktop_uagents
  end
end   # End user agent definition function


def validate_cidr(cidr_to_val)
  # Function used to determine if the user provided CIDR range is valid
  begin
    cidr_test = NetAddr::CIDR.create("#{cidr_to_val}")
    return true
  rescue NetAddr::ValidationError
    return false
  end
end


def web_report_header(real_report_date, real_report_time)
  # Function used to create the beginning of a report page
  web_index_head = "<html>"\
    "<head>"\
    "<link rel=\"stylesheet\" href=\"style.css\" type=\"text/css\"/>"\
    "<title>EyeWitness Report</title>"\
    "</head>"\
    "<body>"\
    "<center>Report Generated on #{real_report_date} at #{real_report_time}</center>"\
    "<br><table border=\"1\">"\
    "<tr>"\
    "<th>Web Request Info</th>"\
    "<th>Web Screenshot</th>"\
    "</tr>"
  return web_index_head
end


#
#
#   Start of main()
#
#

title_screen()

# Parse all the command line arguments
cli_parsed = CliParser.parse(ARGV)

# Determine the path that EyeWitness is in
eyewitness_path = File.expand_path(File.dirname(__FILE__))

# Determine if EyeWitness is only scanning for web servers, or creating a report
if !cli_parsed.localscan.nil?
  if validate_cidr(cli_parsed.localscan)
    scanner(cli_parsed.localscan, eyewitness_path)
  else
    puts "[*] ERROR: You provided an invalid CIDR range."
    puts "[*] ERROR: Please re-start EyeWitness and provide a valid range!"
    exit
  end
  exit
end   # End of if statement for local scan

# If just creating the targets, then parse the input files, and write them out,
# otherwise create the report folders
if !cli_parsed.create_targets.nil?

  puts "Writing out live servers to #{cli_parsed.create_targets}"
  create_target_url_list = []

  if !cli_parsed.nessus_xml.nil?
    nessus_class = NessusParser.new

    parser = Nokogiri::XML::SAX::Parser.new(nessus_class)
    parser.parse(File.open(cli_parsed.nessus_xml))

    create_target_url_list = nessus_class.url_get()

  elsif !cli_parsed.nmap_xml.nil?
    nmap_class = NmapParser.new

    # Function is called specifically when trying to return only IP addresses, not
    # dns names of web servers while parsing nmap xml output
    if cli_parsed.rid_dns
      nmap_class.ip_only()
    end

    parser = Nokogiri::XML::SAX::Parser.new(nmap_class)
    parser.parse(File.open(cli_parsed.nmap_xml))

    create_target_url_list = nmap_class.url_get()

  else
    puts "[*] Error: You need need to provide nmap or nessus xml output files for use"
    puts "[*] Error: with the create targets flag."
    exit
  end   # End of Parsing function for create targets

  # Write out the urls to the user specified file
  File.open(cli_parsed.create_targets, 'w') do |target_writer|
    create_target_url_list.each do |create_target_url|
      target_writer.write("#{create_target_url}\n")
    end
  end

  puts "... and done!"
  exit

# If not just creating targets, then start normal execution flow
else
  # Create the folders that will be used
  report_folder, report_date, report_time = folder_out(cli_parsed.dir_name, eyewitness_path)

  # Log path only used in ghost for SSL cert issues.  If not needed with selenium
  # then this can likely be removed.
  if cli_parsed.dir_name.start_with?('/') or cli_parsed.dir_name.start_with?('C:\\')
    log_file_path = File.join(cli_parsed.dir_name, report_folder, 'logfile.log')
  else
    log_file_path = File.join(report_folder, 'logfile.log')
  end   # End dir name if statement

  # Define a couple default variables
  extra_info = nil
  blank_value = nil
  baseline_request = "Baseline"
  page_length = nil
end   # End of create targets if statement

# If only generating a report on a single website
if !cli_parsed.single_website.nil?

  #  If we're not cycling through user agents, just return the selenium web driver object
  if cli_parsed.cycle == "none"
    eyewitness_selenium_driver = selenium_driver()

  # if we are cycling through user agents, return the user agent hash
  # and the selenium web driver object
  else
    ua_group = user_agent_definition(cli_parsed.cycle)
    eyewitness_selenium_driver = selenium_driver()
  end   # End user agent cycle if statement
  
  # Perform a quick check to make sure website starts with http or https
  # if not, add http to the front
  if cli_parsed.single_website.start_with?('http://') or cli_parsed.single_website.start_with?('https://')
  else
    cli_parsed.single_website = "http://#{cli_parsed.single_website}"
  end

  # Start drafting the report, and get the report html code (the head/start of it)
  web_index = web_report_header(report_date, report_time)
  puts "Trying to screenshot #{cli_parsed.single_website}"

  # Create the filename to store each website's picture
  single_url, source_name, picture_name = file_names(cli_parsed.single_website)

  # If not cycling through user agents, then go to the site, capture screenshot and source code
  if cli_parsed.cycle == "none"
    unused_length_difference = nil
    single_source = capture_screenshot(eyewitness_selenium_driver, report_folder, cli_parsed.single_website)

    # returns back an object that needs to be iterated over for the headers
    single_site_headers_source = source_header_grab(cli_parsed.single_website)

    single_default_creds = default_creds(single_site_headers_source.body, Dir.pwd)

    web_index = table_maker(web_index, cli_parsed.single_website, single_default_creds,
      single_site_headers_source, source_name, picture_name, unused_length_difference, Dir.pwd,
      report_folder)

  end   # Endo of if statement looking for ua cycle

  single_page_report(web_index, report_folder)
  eyewitness_selenium_driver.quit

#  This is hit when providing a file for input for EyeWitness
elsif !cli_parsed.file_name.nil? or !cli_parsed.nessus_xml.nil? or !cli_parsed.nmap_xml.nil?

  # Declare the default values of the variables being used
  final_url_list = []
  total_urls = 0
  
  # Figure out which command line option hit, and then send it to that parser
  if !cli_parsed.file_name.nil?
    final_url_list, total_urls = logistics(cli_parsed.file_name)

  # The nessus parsing class
  elsif !cli_parsed.nessus_xml.nil?
    nessus_class = NessusParser.new

    parser = Nokogiri::XML::SAX::Parser.new(nessus_class)
    parser.parse(File.open(cli_parsed.nessus_xml))

    final_url_list = nessus_class.url_get()
    total_urls = final_url_list.length

  # The nmap parsing class
  elsif !cli_parsed.nmap_xml.nil?
    nmap_class = NmapParser.new

    # Function is called specifically when trying to return only IP addresses, not
    # dns names of web servers while parsing nmap xml output
    if cli_parsed.rid_dns
      nmap_class.ip_only()
    end

    parser = Nokogiri::XML::SAX::Parser.new(nmap_class)
    parser.parse(File.open(cli_parsed.nmap_xml))

    final_url_list = nmap_class.url_get()
    total_urls = final_url_list.length

  end   # End of xml parsing section

  puts "There's a total of #{total_urls} URLs."

  if !cli_parsed.jitter.nil?
    final_url_list = final_url_list.shuffle
  end

  # Create the first part of the report for page 1 of X
  web_index = web_report_header(report_date, report_time)

  # Create a URL counter to know when to go to a new page
  # Create a page counter to track pages
  page_counter = 1
  htmldictionary = {}
  url_counter = 0
  # use this to measure if num URL is measured against max urls per page
  page_url_counter = 0

  # Start looping through all URLs and screenshotting/capturing page source for each
  final_url_list.each do |individual_url|

    # Count the number of URLs, remove the whitespace from the url
    url_counter += 1
    page_url_counter += 1
    individual_url = individual_url.strip

    # Get the file names for the 
    individual_url, source_name, picture_name = file_names(individual_url)

    # Print out message showing the URL being captured, and the number that it is
    puts "Attempting to capture #{individual_url} (#{url_counter}/#{total_urls})"

    if cli_parsed.cycle == "none"
      unused_length_difference = nil
      eyewitness_selenium_driver_multi_site = selenium_driver()
      single_source = capture_screenshot(eyewitness_selenium_driver_multi_site, report_folder, individual_url)
      
      # returns back an object that needs to be iterated over for the headers and source code
      multi_site_headers_source = source_header_grab(individual_url)

      multi_default_creds = default_creds(multi_site_headers_source.body, Dir.pwd)

      web_index = table_maker(web_index, individual_url, multi_site_default_creds,
      multi_site_headers_source, source_name, picture_name, unused_length_difference, Dir.pwd,
      report_folder)

      if !cli_parsed.jitter.nil?
        sleep_value = rand(30)
        sleep_value = sleep_value * .01
        sleep_value = 1 - sleep_value
        sleep_value = sleep_value * cli_parsed.jitter
        puts "[*] Sleeping for #{sleep_value} seconds..."
        sleep(sleep_value)
      end   # End jitter if statement
  end   # End of loop looping through all URLs within final_url_list

    if page_url_counter == cli_parsed.results_number

      if page_counter == 1
        # Close out the html and write it to disk
        web_index += "</table>\n"

        # Get path to where the report will be written, and write it out
        reporthtml = File.join(report_folder, "report.html")
        File.open(reporthtml, 'w') do |first_report_page|
          first_report_page.write(web_index)
        end

        page_counter += 1
        web_index = web_report_header(report_date, report_time)
      else
        web_index += "</table>\n"
        multi_page_reporthtml = File.join(report_folder, "report#{page_counter}.html")
        File.open(multi_page_reporthtml, 'w') do |report_page_out|
          report_page_out.write(web_index)
        end

        #Reset URL counter
        page_counter += 1
        web_index = web_report_header(report_date, report_time)
      end   # End of page counter if statement
    end   # end of if statement where url counter for the page matches max urls per page

    if page_counter == 1
      single_page_report(web_index, report_folder)
    else
      web_index += "</table>\n"
      report_append = File.join(report_folder, "report_page#{page_counter}.html")
      File.open(report_append, 'a') do |report_pages|
        report_pages.write(web_index)
      end

    end   # End page counter final report writeout

  else
    ua_group = user_agent_definition(cli_parsed.cycle)
    eyewitness_selenium_driver_multi_site = selenium_driver()
  end   # End file input user agent cycle if statement



end   # end single website, file, or xml inputs if statement

puts "Done!"


# Set the default values
#options.file_name = nil
#options.nessus_xml = nil
#options.nmap_xml = nil
#options.single_website = nil
#options.create_targets = nil
#options.timeout = 7
#options.jitter = nil
#options.dir_name = "none"
#options.results_number = 25
#options.ua_name = nil
#options.cycle = "none"
#options.difference = 50
#options.skip_creds = false
#options.localscan = nil
#options.rid_dns = false


#File.open("urls.txt", "r") do |f|
#  puts "There's #{f.count} URLs to capture!"
#end

