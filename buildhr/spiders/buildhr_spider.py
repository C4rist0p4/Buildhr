# -*- coding: utf-8 -*-
import scrapy
import pytesseract
import io
import base64
import json
import csv
import os
import numpy as np
from scrapy_splash import SplashRequest
from PIL import Image
from validate_email import validate_email
from imageio import imread
from cv2 import cv2

script = '''
function isempty(s)
  return s == nil or s == ''
end

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

  local img_email = false
  local region = get_bbox(elem, "邮箱")
  if (region ~= false) then
    img_email = splash:jpeg{region=region}
  end

  local img_number = false
  region = get_bbox(elem, "座机")
  if (region ~= false) then
    img_number = splash:jpeg{region=region}
  end


  return {ImgEmail=img_email,ImgNumber=img_number, CompanyName=companyname,OrignalURL=splash.args.url, Website=website}
end
'''


class BuildhrSpiderSpider(scrapy.Spider):
    name = 'buildhr_spider'
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'

    def start_requests(self):

        file_path = os.path.join(os.path.dirname(
            __file__), 'missed_email_10.csv')

        with open(file_path, 'r', encoding='utf8') as in_file:
            csv_reader = csv.DictReader(in_file)

            for url in csv_reader:
                u = url['Orignal Page URL']
                self.logger.info(u)
                # yield scrapy.Request(url=u, callback=self.parse)
                yield SplashRequest(url=u, callback=self.parse_img, endpoint='execute', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0'}, args={'wait': 3, 'lua_source': script})

    def parse(self, response):
        links = response.xpath('.//a/@href').getall()

        for link in links:
            if '/company/' in link:
                self.logger.info(link)
                yield SplashRequest(url=link, callback=self.parse_img, endpoint='execute', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0'}, args={'wait': 3, 'lua_source': script})

    def parse_img(self, response):
        email = None
        number = None

        data = json.loads(response.body_as_unicode())

        if data['ImgNumber'] != False:
            stream = imread(io.BytesIO(base64.b64decode(data['ImgNumber'])))
            number = self.img_to_text(stream)

        if data['ImgEmail'] != False:

            stream = imread(io.BytesIO(base64.b64decode(data['ImgEmail'])))

            email = self.img_to_text(stream)
            is_valid = validate_email(email)

            if is_valid:
                yield {
                    'Orignal Page URL': data['OrignalURL'],
                    'Company Name': data['CompanyName'],
                    'Phone Number': number,
                    'Website': data['Website'],
                    'EMail': email
                }

            else:
                self.logger.info('Email ' + email)
                yield SplashRequest(url=data['OrignalURL'], callback=self.parse_img, endpoint='execute', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0'}, args={'wait': 3, 'lua_source': script}, dont_filter=True)

        else:
            yield {
                'Orignal Page URL': data['OrignalURL'],
                'Company Name': data['CompanyName'],
                'Phone Number': number,
                'Website': data['Website'],
                'EMail': email
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
