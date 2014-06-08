#!/usr/bin/env ruby

# This is a port of EyeWitness to Ruby, using a new screenshot engine

require 'net/http'
require 'net/https'
require 'nokogiri'
require 'optparse'
require 'ostruct'
require 'pp'
require 'selenium-webdriver'
require 'uri'


class CliParser

  def self.parse(args)

    # Used for a hash-like data structure
    options = OpenStruct.new

    # Set the default values
    options.file_name = nil

    opt_parser = OptionParser.new do |opts|
      opts.banner = "Usage: [options]"

      # Grouped for EyeWitness Input functions
      opts.on("-f", "--filename [Filename]", "File containing URLs to screenshot",
          "each on a new line. NMap XML output",
          "or a .nessus file") do |in_filename|
        options.file_name = in_filename
      end
      opts.on("-s", "--single [URL]", "Single URL to screenshot.") do |single_url|
        options.single_website = single_url
      end
      opts.on("--createtargets [Filename]", "Create file containing web servers",
          "from nmap or nessus output.\n\n") do |target_make|
        options.create_targets = target_make
      end

      # Timing options
      opts.on("-t", "--timeout [7]", Integer, "Maximum number of seconds to wait while",
          "requesting a web page.") do |max_timeout|
        options.timeout = max_timeout
      end
      opts.on("--jitter [15]", Integer, "Number of seconds to use as a base to",
          "randomly deviate from when making requests.\n\n") do |jit_num|
        opts.jitter = jit_num
      end

      # Report output options
      opts.on("-d [Directory Name]", "Name of directory for EyeWitness report.")\
          do |d_name|
        options.dir_name = d_name
      end
      opts.on("--results [25]", Integer, "Number of URLs displayed per page within",
          "the EyeWitness report.\n\n") do |res_num|
        options.results_number = res_num
      end

      # Useragent Options
      opts.on("--useragent [Mozilla/4.0]", "User agent to use when requesting all",
          "websites with EyeWitness.") do |ua_string|
        options.ua_name = ua_string
      end
      opts.on("--cycle [All]", "User agent \"group\" to cycle through when",
          "requesting web pages with EyeWitness.", "Browser, Mobile, Crawler, Scanner,", "Misc, All")\
          do |ua_cycle|
        options.cycle = ua_cycle
      end
      opts.on("--difference [25]", Integer, "Difference threshold to use when comparing",
          "baseline request with modified user", "agent request.\n\n") do |diff_value|
        options.difference = diff_value
      end

      # Local System Options
      opts.on("--open", "Open each URL in a browser as",
          "EyeWitness runs.\n\n") do
        options.open = true
      end

      # Credential Check Options
      opts.on("--skipcreds", "Skip checking for default credentials.\n\n") do
        options.skip_creds = true
      end

      # Local Scanning Options
      opts.on("--localscan [192.168.1.0/24]", "CIDR notation of IP range to scan.\n\n")\
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


class NmapParser < Nokogiri::XML::SAX::Document
  
  def initialize
    @ip_address = nil
    @hostname = nil
    @potential_port = nil
    @final_port_number = nil
    @port_state = nil
    @protocol = nil
  end

  def start_element name, attrs = []
    @attrs = attrs
    
    # Find IP addresses of all machines
    if name == "address"
      @ip_address = Hash[@attrs]['addr']
    end

    if name == "hostname"
      @hostname = Hash[@attrs]['name']
    end

    # Find open ports
    if name == "port"
      @potential_port = Hash[@attrs]['portid']
    end

    # Find port state
    if name == "state"
      if Hash[@attrs]['state'] == "open"
        @port_state = "open"
      else
        @port_state = "closed"
      end
    end

    # Find port "name"
    if name == "service"
      if Hash[@attrs]['name'].include? "https"
        @protocol = "https://"
        @final_port_number = @potential_port
        if @hostname.nil? && @port_state == "open"
          puts "IP: #{@ip_address} Port: #{@final_port_number} and port is #{@port_state}! and uses #{@protocol}!"
        else @port_state == "open"
          puts "IP: #{@hostname} Port: #{@final_port_number} and port is #{@port_state}! and uses #{@protocol}!"
        end
      elsif Hash[@attrs]['name'].include? "http"
        @protocol = "http://"
        @final_port_number = @potential_port
        if @hostname.nil? && @port_state == "open"
          puts "IP: #{@ip_address} Port: #{@final_port_number} and port is #{@port_state}! and uses #{@protocol}!"
        elsif @port_state == "open"
          puts "IP: #{@hostname} Port: #{@final_port_number} and port is #{@port_state}! and uses #{@protocol}!"
        end
      end
    end
  end
end


def default_creds(page_content, full_file_path, local_system_os)

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


def folder_out(dir_name, full_path, local_os)

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
        output_folder_name = "#{date}_#{hours}"
    else
        output_folder_name = dir_name
    end

    output_folder_name = File.join(output_folder_name)

    # Check to see if output folder starts with C:\ or /
    if (output_folder_name.start_with?("C:\\") or output_folder_name.start_with?("/"))
        # Create the paths for making the directories (valid for Win and nix)
        source_out_folder_name = File.join("#{output_folder_name}", "source")
        screen_out_folder_name = File.join("#{output_folder_name}", "screen")
    else
        output_folder_name = File.join(full_path, output_folder_name)
        source_out_folder_name = File.join("#{output_folder_name}", "source")
        screen_out_folder_name = File.join("#{output_folder_name}", "screen")
    end

    # Actually create the directories now
    Dir.mkdir(output_folder_name)
    Dir.mkdir(source_out_folder_name)
    Dir.mkdir(screen_out_folder_name)

    # Write the css file out
    File.open('#{output_folder_name}/style.css', 'w') do |stylesheet|
        stylesheet.puts css_file
    end

    return output_folder_name, current_date, current_time
end # End of folder_out function


def logistics(url_file, target_maker)

  File.open("urls.txt", "r") do |xml_file|
    xml_noko = Nokogiri::XML(xml_file)
  end

end  # End of logistics function


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

  return response
end # End header_grab function


def title_screen()
  system("clear")
  puts "#############################################################################"
  puts "#                               EyeWitness                                  #"
  puts "#############################################################################\n\n"
  return
end # end of title_screen function






title_screen()

cli_parsed = CliParser.parse(ARGV)


File.open("urls.txt", "r") do |f|
  puts "There's #{f.count} URLs to capture!"
end

# Other drivers are available as well http://selenium.googlecode.com/svn/trunk/docs/api/rb/Selenium/WebDriver.html#for-class_method
driver = Selenium::WebDriver.for :firefox

File.open("urls.txt", "r") do |f2|
  f2.each_line do |line|
    driver.navigate.to line.strip
    screenshot_name = line.strip.gsub(':', '').gsub('//', '.').gsub('/', '.')
    screenshot_name = "#{screenshot_name}.png"
    puts screenshot_name
    driver.save_screenshot(screenshot_name)
    puts driver.page_source
  end
end

driver.quit

folder_out()