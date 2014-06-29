#!/usr/bin/env ruby

# This is a port of EyeWitness to Ruby, using a new screenshot engine

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
    options.single_website = nil
    options.create_targets = nil
    options.timeout = 7
    options.jitter = nil
    options.dir_name = nil
    options.results_number = nil
    options.ua_name = nil
    options.cycle = nil
    options.difference = 50
    options.skip_creds = false
    options.localscan = nil

    opt_parser = OptionParser.new do |opts|
      opts.banner = "Usage: [options]"

      # Grouped for EyeWitness Input functions
      opts.on("-f", "--filename Filename", "File containing URLs to screenshot",
          "each on a new line. NMap XML output",
          "or a .nessus file") do |in_filename|
        options.file_name = in_filename
      end
      opts.on("-s", "--single URL", "Single URL to screenshot.") do |single_url|
        options.single_website = single_url
      end
      opts.on("--createtargets Filename", "Create file containing web servers",
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
      opts.on("-d [Directory Name]", "Name of directory for EyeWitness report.")\
          do |d_name|
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


  def url_get
    @url_list
  end
end   # End of nmap parsing class


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
        if @hostname.nil? && @port_state == "open"
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
        if @hostname.nil? && @port_state == "open"
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


  def url_get
    @url_array
  end
end   # End of nmap parsing class


def capture_screenshot(sel_driver, output_path, url_to_grab)
  sel_driver.navigate.to url_to_grab
  screenshot_name = url_to_grab.gsub(':', '').gsub('//', '.').gsub('/', '.')
  sourcecode_name = "#{screenshot_name}.txt"
  screenshot_name = "#{screenshot_name}.png"
  screen_cap_path = File.join(output_path, 'screens', screenshot_name)
  source_code_path = File.join(output_path, 'source', sourcecode_name)
  driver.save_screenshot(screen_cap_path)
  File.open("#{source_code_path}", 'w') do |write_sourcecode|
    write_sourcecode.write(sel_driver.page_source)
  end

  return sel_driver.page_source
end

def default_creds(page_content, full_file_path)

  creds_path = File.join("#{full_file_path}", "signatures.txt")

  begin
    File.open("#{creds_path}", "r") do |signature_file|
      signature_file.each_line do |signature|
        signature_delimeted = signature.split('|')[0]
        default_creds = signature.split('|')[1]

        # Values for signatures not found
        sig_not_found = 0
        all_signatures = signature_delimeted.split(';')
        page_content = page_content.downcase

        all_signatures.each do |individual_signature|
          individual_signature = individual_signature.downcase
          if page_content.include? "#{individual_signature}"
          else
            signature_not_present = true
          end
        end

        if signature_not_present
          return nil
        else
          return default_creds
        end
      end
    end

  rescue Errno::ENOENT
    puts "[*] WARNING Default credentials file not in same directory as EyeWitness!"
    puts "[*] Skipping credential check..."
  end  # End try catch
end  #End of default creds function


def file_names(url_given)

  url_given.gsub('\n', '')
  pic_name = url_given
  source_name = url_given
  source_name = source_name.gsub('://', '').gsub('/', '.').gsub(':', '.')
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
    if dir_name.nil?
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
  encoded = CGI::escape(dangerous_data)
  return encoded
end


def logistics(url_file, target_maker)

  file_urls = []
  num_urls = 0

  begin
    File.open(url_get, "r").each do |url|
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
  report_source += "</table>\n</body>\n</html>"

  report_file = File.join(full_report_path, "report.html")

  File.open(report_file, 'w') do |report_done|
    report_done.write(report_source)
  end
end   # End single page report function


def source_header_grab(url_to_head)
  
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

  web_table_index += "<tr>\n<td><div style=\"display: inline-block; width: 300px; word-wrap:break-word\">
  <a href=\"#{website_url}\" target=\"_blank\">#{website_url}</a><br>".gsub('  ', '')

  if possible_creds.nil?
    encoded_creds = html_encode(possible_creds)
    web_table_index += "<br><b>Default credentials:</b> #{encoded_creds} <br>"
  end

  full_source_path = File.join(output_report_path, "source", source_code_name)

  page_header_source.each_header do |header, value|
    web_table_index += "<br><b>html_encode(#{header}):</b> html_encode(#{value})"
  end

  web_table_index += "<br><br><a href=\"source/#{source_code_name}\"target=\"_blank\">Source Code</a></div></td>
    <td><div id=\"screenshot\" style=\"display: inline-block; width:850px; height 400px; overflow: scroll;\">
    <a href=\"screens/#{screen_shot_name}\" target=\"_blank\"><img src=\"screens/{screen_shot_name}\"
    height=\"400\"></a></div></td></tr>"

  return web_table_index
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
  begin
    cidr_test = NetAddr::CIDR.create("#{cidr_to_val}")
    return true
  rescue NetAddr::ValidationError
    return false
  end
end


def web_report_header(real_report_date, real_report_time)
  web_index_head = "<html>"\
    "<head>"\
    "<link rel=\"stylesheet\" href=\"style.css\" type=\"text/css\"/>"\
    "<title>EyeWitness Report</title>"\
    "</head>"\
    "<body>"\
    "<center>Report Generated on {report_day} at {reporthtml_time}</center>"\
    "<br><table border=\"1\">"\
    "<tr>"\
    "<th>Web Request Info</th>"\
    "<th>Web Screenshot</th>"\
    "</tr>"
  return web_index_head
end


title_screen()

cli_parsed = CliParser.parse(ARGV)

eyewitness_path = File.expand_path(File.dirname(__FILE__))

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

if !cli_parsed.create_targets.nil?
else
  report_folder, report_date, report_time = folder_out(cli_parsed.dir_name, eyewitness_path)

  # Log path only used in ghost for SSL cert issues.  If not needed with selenium
  # then this can likely be removed.
  if cli_parsed.dir_name.start_with?('/') or cli_parsed.dir_name.start_with?('C:\\')
    log_file_path = File.join(cli_parsed.dir_name, report_folder, 'logfile.log')
    report_path = File.join(cli_parsed.dir_name, report_folder)
  else
    log_file_path = File.join(report_folder, 'logfile.log')
    report_path = File.join(Dir.pwd, report_folder)
  end   # End dir name if statement

  if cli_parsed.cycle.nil
    eyewitness_selenium_driver = selenium_driver()
  else
    ua_group = user_agent_definition(cli_parsed.cycle)
    eyewitness_selenium_driver = selenium_driver()
  end   # End user agent cycle if statement

  # Define a couple default variables
  extra_info = nil
  blank_value = nil
  baseline_request = "Baseline"
  page_length = nil
end   # End create targets if statement

if !cli_parsed.single_website.nil?
  
  if cli_parsed.single_website.start_with('http://') or cli_parsed.single_website.start_with('https://')
  else
    cli_parsed.single_website = "http://#{cli_parsed.single_website}"
  end

  web_index = web_report_header(report_date, report_time)
  puts "Trying to screenshot #{cli_parsed.single_website}"

  # Create the filename to store each website's picture
  single_url, source_name, picture_name = file_names(cli_parsed.single_website)

  if cli_parsed.cycle.nil?
    unused_length_difference = nil
    single_source = capture_screenshot(eyewitness_selenium_driver, report_path, cli_parsed.single_website)

    # returns back an object that needs to be iterated over for the headers
    single_site_headers_source = source_header_grab(cli_parsed.single_website)

    single_default_creds = default_creds(single_side_headers_source.body, Dir.pwd)

    web_index = table_maker(web_index, cli_parsed.single_website, single_default_credentials,
      single_site_headers_source, source_name, picture_name, unused_length_difference, Dir.pwd,
      report_path)

  end   # Endo of if statement looking for ua_name
  single_report_page(web_index, report_path)
end   # end single website if statement

puts "Done!"



# Set the default values
#options.file_name = nil
#options.single_website = nil
#options.create_targets = nil
#options.timeout = 7
#options.jitter = nil
#options.dir_name = nil
#options.results_number = nil
#options.ua_name = nil
#options.cycle = nil
#options.difference = 50
#options.skip_creds = false
#options.localscan = nil


#File.open("urls.txt", "r") do |f|
#  puts "There's #{f.count} URLs to capture!"
#end



#File.open("urls.txt", "r") do |f2|
#  f2.each_line do |line|
#    driver.navigate.to line.strip
#    screenshot_name = line.strip.gsub(':', '').gsub('//', '.').gsub('/', '.')
#    screenshot_name = "#{screenshot_name}.png"
#    puts screenshot_name
#    driver.save_screenshot(screenshot_name)
#    puts driver.page_source
#  end
#end

#driver.quit

