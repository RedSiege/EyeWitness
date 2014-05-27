#!/usr/bin/env ruby

# This is a port of EyeWitness to Ruby, using a new screenshot engine

require 'selenium-webdriver'

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
