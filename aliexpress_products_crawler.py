#!/usr/bin/env python
from bs4 import BeautifulSoup
import requests
import re
import json
import csv
import pandas as pd
import time

"""
Functions for create a list of proxy for bypass
"""
def getProxiesDict(proxies_file):
    prox_dict = {}
    with open(proxies_file, mode = 'r') as prox_file:
        reader = csv.reader(prox_file)

        for row in reader:
            ip, port = row
            prox_dict[ip] = port

    return prox_dict

def getProxy(ip, prox_dict):
    proxy_ip = ip
    proxy_port = prox_dict[ip]

    http_proxy  = "http://{}:{}".format(proxy_ip, proxy_port)
    https_proxy = "https://{}:{}".format(proxy_ip, proxy_port)
    ftp_proxy   = "ftp://{}:{}".format(proxy_ip, proxy_port)

    proxyDict = { 
                  "http"  : http_proxy, 
                  "https" : https_proxy, 
                  "ftp"   : ftp_proxy
                }
    return proxyDict

"""
Create Aliexpress.com Crawler
"""
class AliCrawler:

    def __init__(self):
        self.alidomain = 'aliexpress.com'

    def getItemById(self, item_id, proxyDict, store_stats=False):
        url = 'http://www.%s/item/-/%s.html' % (self.alidomain, item_id)
        req = requests.get(url, proxies = proxyDict)
        html = req.text
        bs4 = BeautifulSoup(html, "html5lib")

        data = {}
        data['title'] = bs4.select('h1.product-name')[0].string
        data['original_price'] = float(bs4.select('#j-sku-price')[0].string.split(' ')[0])
        data['link'] = req.url

        #
        # image variants
        #
        #data['image1'] = bs4.select('meta[property=og:image]')[0].attrs['content']
        #data['image2'] = bs4.select('a.ui-image-viewer-thumb-frame img')[0].attrs['src']

        img_script = [f for f in bs4.find_all('script') if 'window.runParams.imageDetailPageURL' in f.text][0]

        img_script = img_script.text.replace('\n', '')
        img_script = img_script.replace('\t', '')

        blocks = re.findall(r"window\.runParams\.imageBigViewURL=\[(.*)\];", img_script)
        images = [b.replace('"', '') for b in blocks[0].split(',')]
        data['image_variants_count'] = len(images)
        data['image_variants_links'] = images

        #
        # rating
        #
        try:
            data['rating'] = float(bs4.select('span[itemprop=ratingValue]')[0].string)
        except:
            data['rating'] = 0.0

        #
        # orders
        #
        try:
            data['orders'] = int(bs4.select('span.orders-count')[0].b.string)
        except:
            data['orders'] = 0

        #
        # discount_price
        #
        try:
            discount_price = bs4.select('#j-sku-discount-price')[0]
            if discount_price.span:
                data['discount_price'] = float(discount_price.span.string)
            else:
                data['discount_price'] = float(discount_price.string)
        except:
            data['discount_price'] = data['original_price']

        #
        # unit_price
        #
        try:
            data['piece_price'] = float(bs4.select('#sku-per-piece-price')[0].string)
        except:
            data['piece_price'] = data['discount_price']

        data['pieces'] = 1
        if(data['piece_price'] != data['discount_price'] and data['piece_price'] > 0):
            data['pieces'] = int(round(data['discount_price']/data['piece_price']))

        #
        # store
        #
        store = bs4.select('a.store-lnk')[0]
        data['store_name'] = store.string
        data['store_link'] = store.attrs['href']
        data['store_id'] = int(bs4.select('#hid_storeId')[0].attrs['value'])

        #
        # offline
        #
        data['offline'] = True
        try:
            offline = re.findall('window.runParams.offline=(\w+);', html)[0]
            if offline == "false":
                data['offline'] = False
        except:
            pass

        #
        # store stats
        #
        if store_stats and not data['offline']:
            try:
                admin_id = int(re.findall('window.runParams.adminSeq="(\w+)";', html)[0])
                stats = self.getSellerStatsByAdminId(admin_id)
                data['store_perc'] = float(stats[1])
                data['store_points'] = int(stats[3])
            except:
                data['store_perc'] = None
                data['store_points'] = None

        #
        # shipping
        #
        data['shipping'] = 0.0
        if not data['offline']:
            data['shipping'] = self.getItemShippingById(item_id)

        return data

    def getItemShippingById(self, item_id):
        url = ('http://freight.%s/ajaxFreightCalculateService.htm'
            '?callback=json&f=d&userType=cnfm&country=BR&count=1'
            '&currencyCode=USD&productid=%s' % (self.alidomain, item_id))

        try:
            req = requests.get(url)
            data = json.loads(req.text[5:-1])
            prices = []
            for shipment in data['freight']:
                prices.append(float(shipment['price']))
            shipping = min(prices)
        except:
            shipping = None

        return shipping

    def getSellerStatsByAdminId(self, admin_id):
        url = ('http://www.%s/cross-domain/feedback/index.html'
            '?memberType=seller&ownerMemberId=%d' % (self.alidomain, admin_id))

        try:
            req = requests.get(url)
            data = req.text.split('\n')[1].split(',')
        except:
            data = []

        return data

    def getListItemsFromSearch(self, item_name):
        prox_dict = getProxiesDict('proxies.csv')
        data = {} # dict of out data
        df = pd.DataFrame() # Initial DataFrame for output
        export_file_name = 'aliexpress_products_%s.csv' % (item_name)
        timeout = time.time() + 60*1

        # Count Number of All Items
        for ip in prox_dict:
            proxyDict = getProxy(ip, prox_dict)
            print('Getting Items Total Count.... {}'.format(proxyDict))
            url = 'http://www.%s/wholesale?catId=0&initiative_id=&SearchText=%s' % (self.alidomain, item_name)

            try:
                req = requests.get(url, proxies = proxyDict)
                html = req.text
                bs4 = BeautifulSoup(html, "html5lib")
            
                # Count Number of All Items
                data['search_count'] = bs4.select(".search-count")[0].string
                print('Items Total Count: ', data['search_count'])
                break

            except:
                continue

        max_count = int(data['search_count'].replace(',', ''))
        if not max_count:
            print('Cannot find any Items! Or sonething went wrong!')
            return
        if max_count >= 5000:
            max_page_num = 100
        else:
            max_page_num = int((max_count)/50) + 1

        # Get All Items Ids
        ids_list = {}
        for page_num in range(1,max_page_num):
            print('Max Possible Page: {}'.format(max_page_num))
            url = 'http://www.%s/wholesale?catId=0&initiative_id=&SearchText=%s&page=%d' % (self.alidomain, item_name, page_num)
            
            ids = {}
            for ip in prox_dict:
                proxyDict = getProxy(ip, prox_dict)
                print('Get Ids: {}'.format(proxyDict))
                
                try:
                    req = requests.get(url, proxies = proxyDict)
                    html = req.text
                    bs4 = BeautifulSoup(html, "html5lib")

                    # Get List of Item Ids per page
                    ids_script = [f for f in bs4.find_all('script') if '"object_ids":' in f.text][0]
                    ids_script = ids_script.text
                    
                    blocks = re.findall(r'"object_ids":"(.*);",', ids_script)[0]
                    ids = dict([b.split(',') for b in blocks.split(';')])
                    break

                except:
                    continue

            # Update Ids List
            ids_list.update(ids)
            print('New Id Number: {}, Total: {}'.format(len(ids), len(ids_list)))

            # Write Item Data to File / Updating after each loop
            if len(ids) > 0:
                # Update Id List File Out
                with open('ids_list.csv', 'a') as f:
                    for i in ids:
                        writer = csv.writer(f)
                        writer.writerow([i, ids[i]])

                # Updating Item Data after each loop
                i = 1
                for item_id in ids:
                    print('Page {}/{} : {}/{}'.format(page_num, max_page_num, i, len(ids)))
                    try:
                        item_data = self.getItemById(item_id)
                    except:
                        for ip in prox_dict: # Bypass by proxy
                            proxyDict = getProxy(ip, prox_dict)
                            print('getItemData: {}'.format(proxyDict))

                            try:
                                item_data = self.getItemById(item_id, proxyDict)
                                break
                            except:
                                continue

                        out_data = [(item_id, item_data['title'], item_data['original_price'], item_data['link'], item_data['image_variants_count'], '; '.join(item_data['image_variants_links']))]

                        new_df = pd.DataFrame(out_data, columns = ['ITEM_ID', 'ITEM_TITLE', 'ITEM_OR_PRICE', 'ITEM_LINK', 'ITEM_IMG_COUNT', 'ITEM_IMG_LINKS'])

                        df = pd.concat([df, new_df]).drop_duplicates().reset_index(drop=True)
                        df.to_csv(export_file_name)

                    i += 1

        data['ids_list'] = ids_list

        return data


if __name__ == "__main__":
    ali = AliCrawler()

    item_name = input('Type Item Name for Search: ')
    ali.getListItemsFromSearch(item_name)

    # ids = "32847338541,32847882555"
    # for id in ids.split(","):
    #     print("===== %d" % int(id))
    #     title = ali.getItemById(int(id))['title']
    #     image_variants_links = ali.getItemById(int(id))['image_variants_links']
    #     original_price = ali.getItemById(int(id))['original_price']
    #     print('{}\n{}\n{}'.format(title, image_variants_links, original_price))