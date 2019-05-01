# -*- coding: utf-8 -*-
import scrapy
import pytesseract
import io
import base64
import json
import csv
from PIL import Image
from scrapy_splash import SplashRequest

script = ''' 
function isempty(s)
  return s == nil or s == ''
end

function main(splash, args)

  assert(splash:go(splash.args.url))
  assert(splash:wait(0.5))
  
  splash:set_viewport_full()

  local get_img = splash:jsfunc([[
    function (element) {  
      var el = element.parentElement;
      var r = el.getBoundingClientRect();
      return [r.left+8, r.top, r.right, r.bottom];
    }
  ]])
  
  local elements = splash:select_all("ul.contact > li > p.cons > img")
	local img = {}
  
  for i, element in ipairs(elements) do
       local region = get_img(element)
       img[i] = splash:jpeg{region=region}
  end  
	
  return {jpeg=img, OrignalURL=splash.args.url} 
end 

local companyname = splash:select("div.details-of-right > h2")
local website = splash:select("ul.contact > li > p.cons  > a")

if isempty(website) then
  website = ""
else
    website = website:text()
end
  
if isempty(companyname) then
  companyname = ""
else
    companyname = companyname:text()
end
  
return {jpeg=img,CompanyName=companyname,OrignalURL=splash.args.url, Website=website} 
end
'''

class BuildhrSpiderSpider(scrapy.Spider):
    name = 'buildhr_spider'
 
    def start_requests(self):
        urls = []
        with open('/Users/christoph/Projekte/buildhr/buildhr/email_run_2.csv', 'r', encoding='utf8') as in_file:
          csv_reader = csv.DictReader(in_file)
          for url in csv_reader:
            self.logger.info(url['URL'])
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
      
        links = response.xpath('.//a/@href').getall()
        for link in links:
            if '/company/' in link:
                yield SplashRequest(url=link, callback=self.parse_img, endpoint='execute', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0'} ,args={'wait': 3,'lua_source': script}) 
                

    def parse_img(self, response):
        email = []
        number = []

        data = json.loads(response.body_as_unicode())
       
        for i in data['jpeg']:           
            stream = io.BytesIO(base64.b64decode(data['jpeg'][i]))
            text = pytesseract.image_to_string(Image.open(stream))
            if "@" in text:
                email.append(text)
            else:
                number.append(text)
        
        yield {
            'Orignal Page URL': data['OrignalURL'],
            'Company Name': data['CompanyName'],
            'Phone Number': number,
            'Website': data['Website'],
            'EMail': email
        }