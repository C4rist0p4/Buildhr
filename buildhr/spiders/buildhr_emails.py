# -*- coding: utf-8 -*-
from PIL import Image
from scrapy_splash import SplashRequest
import scrapy
import pytesseract
import io
import base64
import json
import csv

script = ''' 
function pad(r)
  return {r[1]-46, r[2]-1, r[3]+46, r[4]+1}
end

function main(splash, args)
  -- this function returns element bounding box
  local get_bbox = splash:jsfunc([[
    function(el) {
      var r = el.getBoundingClientRect();
      return [r.left, r.top, r.right, r.bottom];
    }
  ]])
  
assert(splash:go(splash.args.url))
assert(splash:wait(2))

splash:set_viewport_full()

local elems = splash:select_all("ul.contact > li > p.cons > img")
local img = {}
for i, elem in ipairs(elems) do
     local region = pad(get_bbox(elem))
     img[i] = splash:jpeg{region=region}
end  


return {jpeg=img, OrignalURL=splash.args.url} 
end
'''


class BuildhrSpiderSpider(scrapy.Spider):
    name = 'buildhr_emails'
 
    def start_requests(self):
        with open(r'email_run_2.csv', 'r', encoding='utf8') as in_file:
          csv_reader = csv.DictReader(in_file)
          for url in csv_reader:
            
              self.logger.info(url['Orignal Page URL'])
              yield SplashRequest(url=url['Orignal Page URL'], callback=self.parse_img, endpoint='execute', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0'} ,args={'wait': 3,'lua_source': script}) 
                

    def parse_img(self, response):
        email = []
      
        data = json.loads(response.body_as_unicode())
       
        for i in data['jpeg']:
            
            stream = io.BytesIO(base64.b64decode(data['jpeg'][i]))
            text = pytesseract.image_to_string(Image.open(stream))
            if "@" in text:
                email.append(text)
         
        yield {
            'Orignal Page URL': data['OrignalURL'],
            'EMail': email
        }