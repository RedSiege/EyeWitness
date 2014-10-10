#!/usr/bin/env ruby

# This is a port of EyeWitness to Ruby, using a new screenshot engine

# This gem import checker is from Robin Woods (@digininja).  Thanks for
# the help and showing me how you check for it.  Works awesome :)

begin
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
  require 'similar_text'

rescue LoadError => e
# Trying to catch errors and let user know which gem caused it
if e.to_s =~ /cannot load such file -- (.*)/
  missing_gem = $1
  puts "\nError: #{missing_gem} gem not installed\n"
  puts "\t use: \"bundle install\" to install all required gems or \"gem install netaddr\" to install individually\n\n"
  exit
else
  puts "There was an error loading the gems:"
  puts
  puts e.to_s
  exit
end
end


# Change timeout in Net::HTTP
module Net
    class HTTP
        alias old_initialize initialize

        def initialize(*args)
            old_initialize(*args)
            @read_timeout = 10     # 10 seconds
        end
    end
end


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
    options.skip_sort = false
    options.timeout = 10
    options.jitter = nil
    options.dir_name = "none"
    options.results_number = 25
    options.ua_name = nil
    options.localscan = nil
    options.rid_dns = false
    options.proxy_ip = nil
    options.proxy_port = nil
    options.redirection = nil

    # Check for config's file existance, and if present, read in its values
    begin
      File.open("eyewitness.config", "r") do |config_file|
        config_file.each_line do |config_line|
          if config_line.split("=")[0].downcase == "timeout"
            options.timeout = config_line.split("=")[1].gsub('\n', '').to_i
          elsif config_line.split("=")[0].downcase == "useragent"
            options.ua_name = config_line.split("=")[1].gsub('\n', '')
          elsif config_line.split("=")[0].downcase == "jitter"
            options.jitter = config_line.split("=")[1].gsub('\n', '').to_i
          elsif config_line.split("=")[0].downcase == "results"
            options.results_number = config_line.split("=")[1].gsub('\n', '').to_i
          elsif config_line.split("=")[0].downcase == "nodns"
            options.rid_dns = config_line.split("=")[1].gsub('\n', '')
          elsif config_line.split("=")[0].downcase == "proxy_ip"
            options.proxy_ip = config_line.split("=")[1].gsub('\n', '')
          elsif config_line.split("=")[0].downcase == "proxy_port"
            options.proxy_port = config_line.split("=")[1].gsub('\n', '').to_i
          elsif config_line.split("=")[0].downcase == "redirects"
            options.redirection = config_line.split("=")[1].gsub('\n', '')
          else
            # Do nothing, since we don't care about anything else in the file
          end   # End if statement for reading key => values from the config file
        end   # End looping over each line
      end   # End of the file open
    rescue Errno::ENOENT
      # just do nothing, since no config file is present
    end

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
      opts.on("--skip-sort", "Do not group similar pages together") do |skip_sorter|
        options.skip_sort = true
      end 
      opts.on("--no-dns", "Parse nmap XML and only use IP address,",
          "instead of DNS for web server") do |rid_dns|
        options.rid_dns = true
      end
      opts.on("--createtargets Filename", "Create a file containing web servers",
          "from nmap or nessus output.\n\n") do |target_make|
        options.create_targets = target_make
      end
      opts.on("--redirects", "Show web redirections in the report") do |redir|
        options.redirection = true
      end

      # Proxy Settings for EyeWitness
      opts.on("--proxyip 127.0.0.1", "IP address of web proxy proxy.") do |prox_ip|
        options.proxy_ip = prox_ip
      end
      opts.on("--proxyport 8080", Integer, "Port number of web proxy.\n\n") do |prox_port_num|
        options.proxy_port = prox_port_num
      end

      # Timing options
      opts.on("-t", "--timeout 7", Integer, "Maximum number of seconds to wait for",
          "server headers (timeout of 10 seconds for screenshot).") do |max_timeout|
        options.timeout = max_timeout
      end
      opts.on("--jitter 15", Integer, "Number of seconds to use as a base to",
          "randomly deviate from when making requests.\n\n") do |jit_num|
        options.jitter = jit_num
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

      # Local Scanning Options
      opts.on("--localscan 192.168.1.0/24", "CIDR notation of IP range to scan.\n\n")\
          do |scan_range|
        options.localscan = scan_range
      end

      # Show help and command line flags
      opts.on_tail('-h', '--help', '-?', 'Show this message') do
        puts opts
        exit
      end

    end # end of opt_parser
    begin
      opt_parser.parse!(args)

      if options.single_website.nil? && options.file_name.nil? && options.nessus_xml.nil? && options.nmap_xml.nil? && options.create_targets.nil? && options.localscan.nil?
        puts "[*] Error: You need to provide EyeWitness a valid command!"
        puts "[*] Error: Use --help to show usage options!\n\n"
        exit
      end   # end if statement checking to make sure you gave eyewitness a valid command

      if (!options.proxy_ip.nil? && options.proxy_port.nil?) || (options.proxy_ip.nil? && !options.proxy_port.nil?)
        puts "[*] Error: When using a proxy, you must provide both the IP and port to use!"
        puts "[*] Error: Please restart Eyewitness!\n\n"
        exit
      end   # End if statement if using proxy and gave IP but not port, or vice versa

      return options
    rescue OptionParser::InvalidOption
      puts "[*] Error: Invalid command line option provided!"
      puts "[*] Error: Please restart EyeWitness!\n\n"
      exit
    end # End of try catch for invalid option
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
          if @ip_address == nil
            @ip_address = value
          end
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

           # This is needed for port 8081
           elsif value.include? "blackice"
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

  # do a "try catch" for timeout issues
  begin
    # Function used to capture screenshots with selenium
    sel_driver.get url_to_grab
    screenshot_name = url_to_grab.gsub('://', '.').gsub('/', '.').gsub(':', '.')
    sourcecode_name = "#{screenshot_name}.txt"
    screenshot_name = "#{screenshot_name}.png"
    screen_cap_path = File.join(output_path, 'screens', screenshot_name)
    source_code_path = File.join(output_path, 'source', sourcecode_name)
    sel_driver.save_screenshot(screen_cap_path)
    File.open("#{source_code_path}", 'w') do |write_sourcecode|
      write_sourcecode.write(sel_driver.page_source)
    end
    return sel_driver.page_source, sel_driver.title, source_code_path
  rescue Timeout::Error
    puts "[*] Error: Request Timed out for screenshot..."
    blank_page_source = "TIMEOUTERROR"
    no_title = "Timeout Error"
    return blank_page_source, no_title, source_code_path
  rescue Errno::ECONNREFUSED
    blank_page_source = "CONNREFUSED"
    no_title = "Connection Refused or URL Skipped"
    return blank_page_source, no_title, source_code_path
  rescue Selenium::WebDriver::Error::UnknownError
    blank_page_source = "POSSIBLEXML"
    no_title = "Bad response, or possible XML"
    return blank_page_source, no_title, source_code_path
  rescue Selenium::WebDriver::Error::UnhandledAlertError
    blank_page_source = "POSSIBLEXML"
    no_title = "Bad response, or possible XML"
    return blank_page_source, no_title, source_code_path
  rescue NameError
    blank_page_source = "POSSIBLEXML"
    no_title = "Bad response, or possible XML"
    return blank_page_source, no_title, source_code_path
  rescue
    blank_page_source = "UNKNOWNERROR"
    no_title = "Unknown error when connecting to web server"
    return blank_page_source, no_title, source_code_path
  end
end

def default_creds(source_code_path, full_file_path)

  # This function parses the signatures file, and compares it with the source code
  # of the site connected to, and determines if there is a match
  creds_path = File.join("#{full_file_path}", "signatures.txt")

  # Create the blank variable which will store the web page's source code
  page_content = ''

  begin
    # Open the page, and read the source code into the variable
    File.open("#{source_code_path}", "r") do |source_code|
      source_code.each_line do |source_line|
        page_content += source_line
      end
    end
  rescue Errno::ENOENT
    puts "[*] WARNING source code file not found!"
    puts "[*] Skipping credential check..."
    return nil
  end  # End try catch

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


def fetch(uri_str, url_list, limit = 10)
  # This checks up to 10 redirects.  If it keeps going further, change the limit value
  raise ArgumentError, 'HTTP redirect too deep' if limit == 0

  uri = URI.parse(uri_str)

  if uri_str.start_with?("http://")
    # code came from - http://www.rubyinside.com/nethttp-cheat-sheet-2940.html
    http = Net::HTTP.new(uri.host, uri.port)
    request = Net::HTTP::Get.new(uri.request_uri)
  elsif uri_str.start_with?("https://")
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = true
    http.verify_mode = OpenSSL::SSL::VERIFY_NONE
    request = Net::HTTP::Get.new(uri.request_uri)
  end

  response = http.request(request)
  case response
  when Net::HTTPSuccess
    url_list.push("<b>#{uri_str}</b> <- Final URL<br>")
  when Net::HTTPRedirection
    url_list.push("<b>#{uri_str}</b> redirects to...<br>")
    uri = URI.parse(uri_str)
    base_url = "#{uri.scheme}://#{uri.host}"
    new_url = URI.parse(response.header['location'])
    if (new_url.relative?)
      new_url = base_url + response.header['location']
      fetch(new_url, url_list, limit - 1)
    else
      fetch(response['location'], url_list, limit - 1)
    end
  else
    response.error!
  end
end


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
      if File.directory?(output_folder_name)
        puts "[*] ERROR: Folder specified already exists!"
        puts "[*] ERROR: Please provide a new directory to write to!"
        exit
      else
        # Create the paths for making the directories (valid for Win and nix)
        source_out_folder_name = File.join("#{output_folder_name}", "source")
        screen_out_folder_name = File.join("#{output_folder_name}", "screens")
      end
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

    # Get the time for the top of the report
    date_time = Time.new
    current_date = "#{date_time.month}/#{date_time.day}/#{date_time.year}"
    current_time = "#{date_time.hour}:#{date_time.min}:#{date_time.sec}"

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
      if url == "" || url == "\n" || url == "\r"
      else
        url = url.strip
        if !url.start_with?('http://') && !url.start_with?('https://')
          url = "http://#{url}"
        end
        file_urls << url
        num_urls += 1
      end
    end
  rescue Errno::ENOENT
    puts "[*] Error: File not valid, or not found."
    puts "[*] Error: Please rerun and provide a valid file!"
    abort
  rescue Errno::EISDIR
    puts "[*] Error: You provided a directory instead of a file!"
    puts "[*] Error: Please rerun and provide a valid input file containing URLS!\n\n"
    abort
  end

  return file_urls, num_urls
end  # End of logistics function


def page_tracker(number_urls, max_links_per_page, total_num_pages, report_table_data, out_rep_folder, day_of_report, time_of_report)
  # Used to track the number of pages that is needed
  if number_urls == max_links_per_page
    if total_num_pages == 1
      # Close out the html and write it to disk
      report_table_data += "</table>\n"

      # Get path to where the report will be written, and write it out
      report_html = File.join(out_rep_folder, "report.html")
      File.open(report_html, 'w') do |first_report_page|
        first_report_page.write(report_table_data)
      end   # End of report writeout
      total_num_pages += 1
      report_table_data = web_report_header(day_of_report, time_of_report)
      number_urls = 0
    else
      report_table_data += "</table>\n"
      multi_page_reporthtml = File.join(out_rep_folder, "report_page#{total_num_pages}.html")
      File.open(multi_page_reporthtml, 'w') do |report_page_out|
        report_page_out.write(report_table_data)
      end
      #Reset URL counter
      total_num_pages += 1
      report_table_data = web_report_header(day_of_report, time_of_report)
      number_urls = 0
    end   # End of page counter if statement
  end   # End if statement if page url counter matches max per page
  return number_urls, total_num_pages, report_table_data
end   # End of page_tracker function


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

  begin
    net1.enumerate.each do |scan_ip|
      ports.each do |scan_port|
        begin
          Timeout.timeout(5) do
            begin
              puts "[*] Attempting to connect to #{scan_ip}:#{scan_port}..."
              s = TCPSocket.new(scan_ip, scan_port)
              s.close
              # Determine if we need to put http or https in front based off of port number
              if scan_port == 443 or scan_port == 8443
                live_webservers << "https://#{scan_ip}:#{scan_port}"
                puts "[*][*] #{scan_ip} looks to be listening on #{scan_port}."
              else
                live_webservers << "http://#{scan_ip}:#{scan_port}"
                puts "[*][*] #{scan_ip} looks to be listening on #{scan_port}."
              end
            rescue Errno::ECONNREFUSED, Errno::EHOSTUNREACH, Errno::ENETUNREACH
              puts "[*] Error: Unable to connect to host or network (#{scan_ip}:#{scan_port})"
            end
          end
        rescue Timeout::Error
        end
      end   # End port iterator
    end   # End of ip iterator
  rescue Interrupt
    puts "[*][*] You just rage quit the scanner!"
    server_out_file = File.join(tool_path, "scanneroutput.txt")

    File.open(server_out_file, 'w') do |srv_out|
      live_webservers.each do |web_srv|
        srv_out.write("#{web_srv}\n")
      end
    end
    puts "[*][*] Wrote out the results to scanneroutput.txt"
    puts "[*][*] The pool on the roof must have a leak..."
  end

  server_out_file = File.join(tool_path, "scanneroutput.txt")

  File.open(server_out_file, 'w') do |srv_out|
    live_webservers.each do |web_srv|
      srv_out.write("#{web_srv}\n")
    end
  end
end   # End of scanner function


def selenium_driver(possible_user_agent, possible_proxy_ip, possible_proxy_port)
  # Other drivers are available as well 
  #http://selenium.googlecode.com/svn/trunk/docs/api/rb/Selenium/WebDriver.html#for-class_method

  if !possible_user_agent.nil?
    if !possible_proxy_ip.nil? && !possible_proxy_port.nil?
      profile = Selenium::WebDriver::Firefox::Profile.new
      profile['general.useragent.override'] = "#{possible_user_agent}"
      profile['network.proxy.type'] = 1
      profile['network.proxy.http'] = possible_proxy_ip
      profile['network.proxy.http_port'] = possible_proxy_port
      profile['network.proxy.ssl'] = possible_proxy_ip
      profile['network.proxy.ssl_port'] = possible_proxy_port
      driver = Selenium::WebDriver.for :firefox, :profile => profile
    else
      profile = Selenium::WebDriver::Firefox::Profile.new
      profile['general.useragent.override'] = "#{possible_user_agent}"
      driver = Selenium::WebDriver.for :firefox, :profile => profile
    end   # End checking for proxy within user agent name
  elsif !possible_proxy_ip.nil? && !possible_proxy_port.nil?
    profile = Selenium::WebDriver::Firefox::Profile.new
    profile['network.proxy.type'] = 1
    profile['network.proxy.http'] = possible_proxy_ip
    profile['network.proxy.http_port'] = possible_proxy_port
    profile['network.proxy.ssl'] = possible_proxy_ip
    profile['network.proxy.ssl_port'] = possible_proxy_port
    driver = Selenium::WebDriver.for :firefox, :profile => profile
  else
    driver = Selenium::WebDriver.for :firefox
  end   #  End checking if using a user agent or not
  
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


def source_header_grab(url_to_head, total_timeout, trace_redirect)

  invalid_ssl = false

  # All of this code basically grabs the server headers and source code of the
  # provided URL
  # Code for timeout - http://stackoverflow.com/questions/8014291/making-http-head-request-with-timeout-in-ruby
  uri = URI.parse("#{url_to_head}")
  
  if url_to_head.start_with?("http://")
    # code came from - http://www.rubyinside.com/nethttp-cheat-sheet-2940.html
    http = Net::HTTP.new(uri.host, uri.port)
    http.read_timeout = total_timeout
    request = Net::HTTP::Get.new(uri.request_uri)
  elsif url_to_head.start_with?("https://")
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = true
    http.read_timeout = total_timeout
    request = Net::HTTP::Get.new(uri.request_uri)
  else
    puts "[*] Error: Error with URL, please investigate!"
    exit
  end # end if statement for starting with http:// or https://

  if trace_redirect
    # Array containing redirected urls
    all_redirects = []
    fetch(url_to_head, all_redirects)
  end   # End trace redirect if statement

  begin
    # actually make the request
    response = http.request(request)
  rescue OpenSSL::SSL::SSLError
    invalid_ssl = true
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = true
    http.verify_mode = OpenSSL::SSL::VERIFY_NONE
    request = Net::HTTP::Get.new(uri.request_uri)
    begin
      response = http.request(request)
    rescue OpenSSL::SSL::SSLError
      puts "[*] Error: SSL Error connecting to #{url_to_head}"
      response = "SSLERROR"
    end
  rescue Timeout::Error
    response = "TIMEDOUT"
  rescue Errno::ECONNREFUSED
    response = "CONNECTIONDENIED"
  rescue Errno::ECONNRESET
    response = "CONNECTIONDENIED"
  rescue SocketError
    response = "BADURL"
  rescue
    response = "UNKNOWNERROR"
  end

  # Return the response object
  # response.each gives header info
  if response.respond_to?('code')
    if response.code == "401"
      response = "UNAUTHORIZED"
    end
  end
  return response, invalid_ssl, all_redirects
end   # End header_grab function


def table_maker(web_report_html, website_url, possible_creds, page_header_source, source_code_name,
  screenshot_name, length_difference, iwitness_dir, output_report_path, potential_blank, bad_ssl,
  page_title, redirect_list, check_redirs)

  web_report_html += "<tr>\n<td><div style=\"display: inline-block; width: 300px; word-wrap:break-word\">\n"
  web_report_html += "<a href=\"#{website_url}\" target=\"_blank\">#{website_url}</a><br>"

  # If there's any creds identified by EyeWitness, add them to the report
  if !possible_creds.nil?
    encoded_creds = html_encode(possible_creds)
    web_report_html += "<br><b>Default credentials:</b> #{encoded_creds} <br>"
  end

  # If EyeWitness encountered any of the identified errors, add it to the report
  if page_header_source == "CONNECTIONDENIED"
    web_report_html += "CONNECTION REFUSED FROM SERVER!</div></td><td> Connection Refused from server!</td></tr>"
  elsif page_header_source == "TIMEDOUT"
    web_report_html += "Connection to web server timed out!</div></td><td> Connection to web server timed out!</td></tr>"
  elsif page_header_source == "UNAUTHORIZED"
    web_report_html += "Can't auth to page (Basic auth?)!</div></td><td> Can't authenticate to web page (Basic auth?)</td></tr>"
  elsif page_header_source == "UNKNOWNERROR"
    web_report_html += "Unknown error when connecting to web server!</div></td><td> Unknown error when connecting to web server.  Please contact developer and give him details (like the URL) to investigate this!</td></tr>"
  elsif page_header_source == "BADURL"
    web_report_html += "Potentially unable to resolve URL!</div></td><td> Potentially unable to resolve URL!</td></tr>"
  elsif page_header_source == "SSLERROR"
    web_report_html += "SSL Error when connecting to website! </div></td><td> SSL Error when connecting to website!</td></tr>"
  else
    full_source_path = File.join(output_report_path, "source", source_code_name)

    encoded_title_header = html_encode("Page Title")
    begin
      encoded_title = html_encode(page_title)
    rescue
      encoded_title = "Unable to Render"
    end
    web_report_html += "<br><b>#{encoded_title_header}:</b> #{encoded_title}"
    page_header_source.each do |header, value|
      encoded_header = html_encode(header)
      encoded_value = html_encode(value)
      web_report_html += "<br><b>#{encoded_header}:</b> #{encoded_value}"
    end

    if bad_ssl
      web_report_html += "<br><br><b>Invalid SSL Certificate</b>"
    end

    if check_redirs
      web_report_html += "<br><br><b>Redirects:</b><br><br>"
      if redirect_list.length == 1
        web_report_html += "<br><br>No Redirections"
      else
        redirect_list.each do |ind_url|
          web_report_html += "#{ind_url}"
        end
      end
      web_report_html += "<br>"
    end

    web_report_html += "<br><br><a href=\"source/#{source_code_name}\" target=\"_blank\">Source Code</a></div></td>\n"

    if potential_blank == "TIMEOUTERROR"
      web_report_html += "<td>REQUEST TIMED OUT WHILE ATTEMPTING TO CONNECT TO THE WEBSITE!</td></tr>"
    else
      web_report_html += "<td><div id=\"screenshot\" style=\"display: inline-block; width:850px; height 400px; overflow: scroll;\">
        <a href=\"screens/#{screenshot_name}\" target=\"_blank\"><img src=\"screens/#{screenshot_name}\"
        height=\"400\"></a></div></td></tr>".gsub('    ', '')
    end
  end   # End of connection refused if statement

  return web_report_html
end   # End table maker function

def multi_table_maker(html_dictionary, website_url, possible_creds, page_header_source, source_code_name,
  screenshot_name, length_difference, iwitness_dir, output_report_path, potential_blank, bad_ssl, page_title,
  possible_redirs, check_redir)

  html = "\n<tr>\n<td><div style=\"display: inline-block; width: 300px; word-wrap:break-word\">\n"
  html += "<a href=\"#{website_url}\" target=\"_blank\">#{website_url}</a><br>\n"

  if !possible_creds.nil?
    encoded_creds = html_encode(possible_creds)
    html += "<br><b>Default credentials:</b> #{encoded_creds} <br>\n"
  end

  if page_header_source == "CONNECTIONDENIED"
    html += "CONNECTION REFUSED FROM SERVER!</div></td><td> Connection Refused from server!</td></tr>"
  elsif page_header_source == "TIMEDOUT"
    html += "Connection to web server timed out!</div></td><td> Connection to web server timed out!</td></tr>"
  elsif page_header_source == "UNAUTHORIZED"
    html += "Can't auth to page (Basic auth?)!</div></td><td> Can't authenticate to web page (Basic auth?)</td></tr>"
  elsif page_header_source == "UNKNOWNERROR"
    html += "Unknown error when connecting to web server!</div></td><td> Unknown error when connecting to web server.  Please contact developer and give him details (like the URL) to investigate this!</td></tr>"
  elsif page_header_source == "BADURL"
    html += "Potentially unable to resolve URL!</div></td><td> Potentially unable to resolve URL!</td></tr>"
  elsif page_header_source == "SSLERROR"
    html += "SSL Error when connecting to website! </div></td><td> SSL Error when connecting to website!</td></tr>"
  else
    full_source_path = File.join(output_report_path, "source", source_code_name)

    encoded_title_header = html_encode("Page Title")
    begin
      encoded_title = html_encode(page_title)
    rescue
      encoded_title = "Unable to Render"
    end
    html += "<br><b>#{encoded_title_header}:</b> #{encoded_title}\n"
    page_header_source.each_header do |header, value|
      encoded_header = html_encode(header)
      encoded_value = html_encode(value)
      html += "<br><b>#{encoded_header}:</b> #{encoded_value}\n"
    end

    if bad_ssl
      html += "<br><br><b>Invalid SSL Certificate</b>"
    end

    if check_redir
      html += "<br><br><b>Redirects:</b><br><br>"
      if possible_redirs.length == 1
        html += "<br><br>No Redirections"
      else
        possible_redirs.each do |ind_url1|
          html += "#{ind_url1}"
        end
      end
      html += "<br>"
    end

    html += "<br><br><a href=\"source/#{source_code_name}\" target=\"_blank\">Source Code</a></div></td>\n"

    if potential_blank == "TIMEOUTERROR"
      html += "<td>REQUEST TIMED OUT WHILE ATTEMPTING TO CONNECT TO THE WEBSITE!</td></tr>"
    else
      html += "<td><div id=\"screenshot\" style=\"display: inline-block; width:850px; height 400px; overflow: scroll;\">
        <a href=\"screens/#{screenshot_name}\" target=\"_blank\"><img src=\"screens/#{screenshot_name}\"
        height=\"400\"></a></div></td></tr>".gsub('    ', '')
    end
  end   # End of connection refused if statement
  begin
    key = "#{page_title.upcase}|#{website_url}"
  rescue
    key = "Unable to Render|#{website_url}"
  end
  html_dictionary[key] = html
  return html_dictionary
end   # End table maker function


def report_writeout(page_counter, web_index, report_folder)
  if page_counter == 1
    single_page_report(web_index, report_folder)
  else
    web_index += "</table>\n"
    report_append = File.join(report_folder, "report_page#{page_counter}.html")
    File.open(report_append, 'w') do |report_pages|
      report_pages.write(web_index)
    end

    # Create the link structure at the bottom
    link_text = "\n<center><br>Links: <a href=\"report.html\">Page 1</a> "

    # loop over pages and append text to them
    for page in 2..page_counter
      link_text += "<a href=\"report_page#{page}.html\">Page #{page}</a> "
    end
    link_text += "</center>"
    top_links = link_text
    link_text += "\n</body>\n"
    link_text += "</html>"

    # Append link structure to report pages
    report_html = File.join(report_folder, "report.html")
    File.open(report_html, 'a') do |report1_append|
      report1_append.write(link_text)
    end

    # Read in page 1 of report to learn where to add link structure
    p1_counter = 0
    injected_html = ''
    File.open(report_html, 'r') do |report_p1_file|
      report_p1_file.each do |p1_line|
        p1_counter += 1
        injected_html += p1_line
        if p1_counter == 7
          injected_html += top_links
          injected_html += "\n"
        end
      end
    end

    # Write out page 1 of report with link structure at the top
    File.open(report_html, 'w') do |write_p1_report|
      write_p1_report.write(injected_html)
    end

    # Write out link structure to bottom of extra pages
    # Also add links to the top of extra pages (eventually)
    for page_footer in 2..page_counter

      report_pages_append = File.join(report_folder, "report_page#{page_footer}.html")
      File.open(report_pages_append, 'a') do |report_pages_appending|
        report_pages_appending.write(link_text)
      end

      #Counter for reading in lines for each page
      multi_line_counter = 0
      multi_injected_html = ''

      # Read in file and add links to top of page
      File.open(report_pages_append, 'r') do |multi_page_read|
        multi_page_read.each do |multi_page_report_line|
          multi_line_counter += 1
          multi_injected_html += multi_page_report_line
          if multi_line_counter == 7
            multi_injected_html += top_links
            multi_injected_html += "\n"
          end
        end
      end

      # Write out the link structure to top of current page
      File.open(report_pages_append, 'w') do |write_multi_report_page|
        write_multi_report_page.write(multi_injected_html)
      end

    end
  end   # End page counter final report writeout
end   #  End report_writeout function

def title_screen()
  system("clear")
  puts "#############################################################################"
  puts "#                               EyeWitness                                  #"
  puts "#############################################################################\n\n"
  return
end # end of title_screen function


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
  web_index_head = "<html>\n"\
    "<head>\n"\
    "<link rel=\"stylesheet\" href=\"style.css\" type=\"text/css\"/>\n"\
    "<title>EyeWitness Report</title>\n"\
    "</head>\n"\
    "<body>\n"\
    "<center>Report Generated on #{real_report_date} at #{real_report_time}</center>\n"\
    "<br><table border=\"1\">\n"\
    "<tr>\n"\
    "<th>Web Request Info</th>\n"\
    "<th>Web Screenshot</th>\n"\
    "</tr>"
  return web_index_head
end


def web_sorter(web_dict)
  tosort = web_dict.keys
  tosort = tosort.sort do |a,b| a.split("|")[0] <=> b.split("|")[0] end
  web_title = []
  while tosort.length != 0
    item = tosort.shift
    i = 0
    web_title.push(item)
    while i < tosort.length
        if (item.split("|")[0].similar(tosort[i].split("|")[0]) > 80)
            web_title.push(tosort[i])
            tosort.delete_at(i)
        end
        i = i + 1
    end
  end
  return web_title
end   # End web_sorter function


#
#
#   Start of main()
#
#

begin
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

    if cli_parsed.single_website.nil? && cli_parsed.file_name.nil? && cli_parsed.nessus_xml.nil? && cli_parsed.nmap_xml.nil?
      puts "[*] Error: You didn't provide a website to scan!"
      puts "[*] Error: Please re-run and provide valid options!\n\n"
      puts "\"Let me guess... No pool...\""
      exit
    end

    # Define a couple default variables
    extra_info = nil
    blank_value = nil
    baseline_request = "Baseline"
    page_length = nil
  end   # End of create targets if statement

  # If only generating a report on a single website
  if !cli_parsed.single_website.nil?

    # Create the folders that will be used
    report_folder, report_date, report_time = folder_out(cli_parsed.dir_name, eyewitness_path)

    # Log path only used in ghost for SSL cert issues.  If not needed with selenium
    # then this can likely be removed.
    if cli_parsed.dir_name.start_with?('/') or cli_parsed.dir_name.start_with?('C:\\')
      log_file_path = File.join(cli_parsed.dir_name, report_folder, 'logfile.log')
    else
      log_file_path = File.join(report_folder, 'logfile.log')
    end   # End dir name if statement

    # Get the selenium driver
    eyewitness_selenium_driver = selenium_driver(cli_parsed.ua_name, cli_parsed.proxy_ip, cli_parsed.proxy_port)
    eyewitness_selenium_driver.manage.timeouts.page_load = cli_parsed.timeout
    
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
    unused_length_difference = nil
    single_source, page_title, web_source_code = capture_screenshot(eyewitness_selenium_driver, report_folder, cli_parsed.single_website)

    # returns back an object that needs to be iterated over for the headers
    single_site_headers_source, ssl_state, any_redirect = source_header_grab(cli_parsed.single_website, cli_parsed.timeout, cli_parsed.redirection)

    if single_site_headers_source == "CONNECTIONDENIED" || single_site_headers_source == "BADURL" || single_site_headers_source == "TIMEDOUT" || single_site_headers_source == "UNKNOWNERROR" || single_site_headers_source == "SSLERROR" || single_site_headers_source == "UNAUTHORIZED"
      # If we hit this condition, there's no source code to check for default creds, so do nothing
    else
      single_default_creds = default_creds(web_source_code, Dir.pwd)
    end

    web_index = table_maker(web_index, cli_parsed.single_website, single_default_creds,
      single_site_headers_source, source_name, picture_name, unused_length_difference, Dir.pwd,
      report_folder, single_source, ssl_state, page_title, any_redirect, cli_parsed.redirection)

    single_page_report(web_index, report_folder)
    eyewitness_selenium_driver.quit

  #  This is hit when providing a file for input for EyeWitness
  elsif !cli_parsed.file_name.nil? or !cli_parsed.nessus_xml.nil? or !cli_parsed.nmap_xml.nil?

    # Declare the default values of the variables being used
    final_url_list = []
    total_urls = 0
    html_dictionary = Hash.new
    new_webdriver = 0
    
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

    if total_urls == 0
      puts "[*] Error: There's no URLs to scan with EyeWitness!"
      puts "[*] Error: Please re-start EyeWitness and provide a file with URLs!\n\n"
      exit
    end

    # Create the folders that will be used
    report_folder, report_date, report_time = folder_out(cli_parsed.dir_name, eyewitness_path)

    # Log path only used in ghost for SSL cert issues.  If not needed with selenium
    # then this can likely be removed.
    if cli_parsed.dir_name.start_with?('/') or cli_parsed.dir_name.start_with?('C:\\')
      log_file_path = File.join(cli_parsed.dir_name, report_folder, 'logfile.log')
    else
      log_file_path = File.join(report_folder, 'logfile.log')
    end   # End dir name if statement

    puts "There's a total of #{total_urls} URLs..."

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

    # Create the selenium object used to grab each site's screenshot
    eyewitness_selenium_driver_multi_site = selenium_driver(cli_parsed.ua_name, cli_parsed.proxy_ip, cli_parsed.proxy_port)
    eyewitness_selenium_driver_multi_site.manage.timeouts.page_load = cli_parsed.timeout

    # Start looping through all URLs and screenshotting/capturing page source for each
    final_url_list.each do |individual_url|
      begin
        url_counter += 1
        page_url_counter += 1
        new_webdriver += 1
        # Count the number of URLs, remove the whitespace from the url
        individual_url = individual_url.strip
        ssl_current_state = false

        # if we need a new webdriver, do it here
        if new_webdriver == 300
          new_webdriver = 0
          eyewitness_selenium_driver_multi_site.quit
          eyewitness_selenium_driver_multi_site = selenium_driver(cli_parsed.ua_name)
          eyewitness_selenium_driver_multi_site.manage.timeouts.implicit_wait = cli_parsed.timeout
        end

        # Get the file names for the 
        individual_url, source_name, picture_name = file_names(individual_url)

        # Print out message showing the URL being captured, and the number that it is
        puts "Attempting to capture #{individual_url} (#{url_counter}/#{total_urls})"

        unused_length_difference = nil
        single_source, page_title, web_source_code = capture_screenshot(eyewitness_selenium_driver_multi_site, report_folder, individual_url)
        
        # returns back an object that needs to be iterated over for the headers and source code
        multi_site_headers_source, ssl_current_state, potential_redirects = source_header_grab(individual_url, cli_parsed.timeout, cli_parsed.redirection)

        if multi_site_headers_source == "CONNECTIONDENIED" || multi_site_headers_source == "BADURL" || multi_site_headers_source == "TIMEDOUT" || multi_site_headers_source == "UNKNOWNERROR" || multi_site_headers_source == "SSLERROR" || multi_site_headers_source == "UNAUTHORIZED"
          # If we hit this condition, there's no source code to check for default creds, so do nothing
        else
          multi_site_default_creds = default_creds(web_source_code, Dir.pwd)
        end

        # If not grouping page
        if !cli_parsed.skip_sort
          html_dictionary = multi_table_maker(html_dictionary, individual_url, multi_site_default_creds,
          multi_site_headers_source, source_name, picture_name, unused_length_difference, Dir.pwd,
          report_folder, single_source, ssl_current_state, page_title, potential_redirects, cli_parsed.redirection)
        else
          web_index = table_maker(web_index, individual_url, multi_site_default_creds,
          multi_site_headers_source, source_name, picture_name, unused_length_difference, Dir.pwd,
          report_folder, single_source, ssl_current_state, page_title, potential_redirects, cli_parsed.redirection)
        end

        if !cli_parsed.jitter.nil?
          sleep_value = rand(30)
          sleep_value = sleep_value * 0.01
          sleep_value = 1 - sleep_value
          sleep_value = sleep_value * cli_parsed.jitter
          puts "[*] Sleeping for #{sleep_value} seconds..."
          sleep(sleep_value)
        end   # End jitter if statement

      rescue Interrupt
        puts "[*] EXIT: You just rage quit with Ctrl+C!"
        if !cli_parsed.skip_sort
          keys = web_sorter(html_dictionary)

          # Key counter for tracking URLs per page when sorting the results
          key_counter = 0

          keys.each do |key|
            key_counter, page_counter, web_index = page_tracker(key_counter, cli_parsed.results_number, page_counter, web_index, report_folder, report_date, report_time)
            web_index += html_dictionary[key]
            key_counter += 1
          end
        end   # End of second cli_parsed.skip_sort if statement
        report_writeout(page_counter, web_index, report_folder)
        final_report_path = File.join(report_folder)
        puts "[*] We wrote out what we could! Check out the report at #{final_report_path}"
        puts "[*] Have a good one!"
        exit
      end

      if cli_parsed.skip_sort
        page_url_counter, page_counter, web_index = page_tracker(page_url_counter, cli_parsed.results_number, page_counter, web_index, report_folder, report_date, report_time)
      end
    end   # End of loop looping through all URLs within final_url_list

    if !cli_parsed.skip_sort
      keys = web_sorter(html_dictionary)

      # Key counter for tracking URLs per page when sorting the results
      key_counter = 0

      keys.each do |key|
        key_counter, page_counter, web_index = page_tracker(key_counter, cli_parsed.results_number, page_counter, web_index, report_folder, report_date, report_time)
        web_index += html_dictionary[key]
        key_counter += 1
      end
    end   # End of second cli_parsed.skip_sort if statement

    report_writeout(page_counter, web_index, report_folder)

    #  Close the selenium object for file based input
    eyewitness_selenium_driver_multi_site.quit
  end   # end single website, file, or xml inputs if statement

  final_report_path = File.join(report_folder)
  puts "[*] Done! Check out the report at #{final_report_path}"
rescue Interrupt
  puts "[*] Error: You juse rage quit via Ctril+C!"
  puts "[*] Error: Just re-start EyeWitness to use it again!\n\n"
  puts "\"If I win, you wear a dress.\" \"And if I win, you do too.\" \"...Deal\""
  exit
end
