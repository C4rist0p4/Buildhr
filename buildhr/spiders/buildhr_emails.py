# -*- coding: utf-8 -*-
import scrapy
import pytesseract
import io
import base64
import json
import csv
import os
import numpy as np
from validate_email import validate_email
from imageio import imread
from cv2 import cv2
from scrapy_splash import SplashRequest

script = '''
function main(splash, args)

assert(splash:go(splash.args.url))
assert(splash:wait(12))
splash:set_viewport_full()

  local get_bbox = splash:jsfunc([[
    function(element, search_parameter) {
			var elements_p = document.getElementsByClassName('tits');

    	var element_coordinates = false;
    	var i;
      for (i = 0; i < elements_p.length; i++) {
        if (elements_p[i].textContent == search_parameter) {
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
local region = get_bbox(elem, "邮箱")
if (region ~= false) then
   img = splash:jpeg{region=region}
end

return {jpeg=img, OrignalURL=splash.args.url}
end
'''


class BuildhrSpiderSpider(scrapy.Spider):
    name = 'buildhr_emails'

    def start_requests(self):

        file_path = os.path.join(os.path.dirname(
            __file__), 'missed_email_10.csv')

        with open(file_path, 'r', encoding='utf8') as in_file:
            csv_reader = csv.DictReader(in_file)

            for url in csv_reader:
                self.logger.info(url['Orignal Page URL'])
                yield SplashRequest(url=url['Orignal Page URL'], callback=self.parse_img, endpoint='execute', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0'}, args={'wait': 3, 'lua_source': script})

    def parse_img(self, response):

        data = json.loads(response.body_as_unicode())

        if data['jpeg'] != False:

            stream = imread(io.BytesIO(base64.b64decode(data['jpeg'])))

            email = self.img_to_text(stream)
            is_valid = validate_email(email)

            if is_valid:
                yield {
                    'Orignal Page URL': data['OrignalURL'],
                    'EMail': email
                }
            else:
                self.logger.info('Email ' + email)
                yield SplashRequest(url=data['OrignalURL'], callback=self.parse_img, endpoint='execute', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0'}, args={'wait': 3, 'lua_source': script}, dont_filter=True)
        else:
            yield {
                'Orignal Page URL': data['OrignalURL'],
                'EMail': 'NO Email'
            }

    def img_to_text(self, stream):

        img = cv2.cvtColor(stream, cv2.COLOR_BGR2GRAY)

        img = cv2.resize(img, None, fx=10, fy=10,
                         interpolation=cv2.INTER_CUBIC)

        kernel = np.ones((1, 1), np.uint8)

        img = cv2.dilate(img, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)

        img = cv2.threshold(cv2.GaussianBlur(img, (5, 5), 0),
                            0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        text = pytesseract.image_to_string(img, config='--psm 11')

        return text
