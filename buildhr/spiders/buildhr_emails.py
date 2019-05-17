# -*- coding: utf-8 -*-
import scrapy
import pytesseract
import io
import base64
import json
import csv
import numpy as np
from imageio import imread
from cv2 import cv2
from PIL import Image
from scrapy_splash import SplashRequest

script = '''
function main(splash, args)

assert(splash:go(splash.args.url))
splash:set_viewport_full()

  local get_bbox = splash:jsfunc([[
    function(element) {
			var elements_p = document.getElementsByClassName('tits');

    	var element_coordinates = false;
    	var i;
      for (i = 0; i < elements_p.length; i++) {
        if (elements_p[i].textContent == "邮箱" or elements_p[i].textContent == "邮 箱") {
    			 	var el = elements_p[i].nextElementSibling;
    				var r = el.getBoundingClientRect();
         		element_coordinates = [r.left+8, r.top, r.right, r.bottom];
  			}
      }

    	if (element_coordinates != false) {
    		return element_coordinates
  		} else {
    		return false
  		}
    }
  ]])

local img = false
local region = get_bbox(elem)
if (region ~= false) then
   img = splash:jpeg{region=region}
end

return {jpeg=img, OrignalURL=splash.args.url}
end
'''


class BuildhrSpiderSpider(scrapy.Spider):
    name = 'buildhr_emails'

    def start_requests(self):
        with open(r'C:\Users\Admin\Buildhr\buildhr\spiders\missed_email.csv', 'r', encoding='utf8') as in_file:
            csv_reader = csv.DictReader(in_file)

            for url in csv_reader:
                self.logger.info(url['Orignal Page URL'])
                yield SplashRequest(url=url['Orignal Page URL'], callback=self.parse_img, endpoint='execute', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0'}, args={'wait': 3, 'lua_source': script})

    def parse_img(self, response):
        email = []

        data = json.loads(response.body_as_unicode())

        if data['jpeg'] != False:

            stream = imread(io.BytesIO(base64.b64decode(data['jpeg'])))

            img = cv2.cvtColor(stream, 1)

            img = cv2.resize(img, None, fx=4, fy=4,
                             interpolation=cv2.INTER_CUBIC)

            kernel = np.ones((1, 1), np.uint8)

            img = cv2.dilate(img, kernel, iterations=1)
            img = cv2.erode(img, kernel, iterations=1)

            text = pytesseract.image_to_string(img)

            email.append(text)
        else:
            email.append('NO Email')

        yield {
            'Orignal Page URL': data['OrignalURL'],
            'EMail': email
        }
