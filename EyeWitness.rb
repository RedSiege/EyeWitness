#!/usr/bin/env ruby

# This is a port of EyeWitness to Ruby, using a new screenshot engine

require 'selenium-webdriver'


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

    # Write the css file out
    File.open('style.css', 'w') do |stylesheet|
        stylesheet.puts css_file
    end

    # Check to see if the directory name is null or not
    if dir_name.nil?
        # Get the Time and Date for creating the folder structure
        date_time = Time.new
        date = "#{date_time.month}#{date_time.day}#{date_time.year}"
        hours = "#{date_time.hour}#{date_time.min}#{date_time.sec}"
        output_folder_name = "#{date}_#{hours}"
    else
        output_folder_name = dir_name
    end

    # Create the paths for making the directories (valid for Win and nix)
    output_folder_name = File.join(output_folder_name)
    source_out_folder_name = File.join("#{output_folder_name}", "source")
    screen_out_folder_name = File.join("#{output_folder_name}", "screen")

    # Actually create the directories now
    Dir.mkdir(output_folder_name)
    Dir.mkdir("#{output_folder_name}/source")
    Dir.mkdir("#{output_folder_name}/screens")

    return
end




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
  end
end

driver.quit

folder_out()