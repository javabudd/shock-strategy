#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from kumex.client import Trade, Market
from slack import WebClient


class Shock(object):

    def __init__(self):
        # read configuration from json file
        with open('config.json', 'r') as file:
            config = json.load(file)

        self.api_key = config['api_key']
        self.api_secret = config['api_secret']
        self.api_passphrase = config['api_passphrase']
        self.sandbox = config['is_sandbox']
        self.symbol = config['symbol']
        self.resolution = int(config['resolution'])
        self.valve = float(config['valve'])
        self.leverage = float(config['leverage'])
        self.size = float(config['size'])
        self.market = Market(self.api_key, self.api_secret, self.api_passphrase, is_sandbox=self.sandbox)
        self.trade = Trade(self.api_key, self.api_secret, self.api_passphrase, is_sandbox=self.sandbox)
        self.slack = WebClient(config['slack_token'])
        self.slack_channel = config['slack_channel']

    def error(self, error, message):
        print(message)
        self.slack_message(message)
        time.sleep(self.resolution)

    def create_sell_limit_order(self, price):
        try:
            order = shock.trade.create_limit_order(shock.symbol, 'sell', self.leverage, self.size, price,
                                                   timeInForce='IOC')
            while shock.trade.get_order_details(order['orderId']).get('isActive'):
                print('waiting for order execution...')
        except BaseException as e:
            self.error(e, 'sell order execution failed!')

            return False

        self.slack_message('sell order executed: ' + 'order id =' + order['orderId'])

        return True

    def create_buy_limit_order(self, price):
        try:
            order = shock.trade.create_limit_order(shock.symbol, 'buy', self.leverage, self.size, price,
                                                   timeInForce='IOC')
            while shock.trade.get_order_details(order['orderId']).get('isActive'):
                print('waiting for order execution...')
        except BaseException as e:
            self.error(e, 'buy order execution failed!')

            return False

        self.slack_message('buy order executed: ' + 'order id =' + order['orderId'])

        return True

    def get_position_details(self):
        try:
            details = self.trade.get_position_details(self.symbol)
        except BaseException as e:
            self.error(e, 'position detail retrieval failed!')
            details = None

        return details

    def get_kline_data(self, kline_from, kline_to):
        try:
            kline_data = self.market.get_kline_data(self.symbol, self.resolution, kline_from, kline_to)
        except BaseException as e:
            self.error(e, 'kline retrieval failed!')
            kline_data = None

        return kline_data

    def slack_message(self, message):
        self.slack.chat_postMessage(channel=self.slack_channel, text=message)

    def loop(self):
        while 1:
            print("pepehands")
            time_to = int(time.time() * 1000)
            time_from = time_to - self.resolution * 60 * 35 * 1000
            data = self.get_kline_data(time_from, time_to)

            if data is None:
                continue

            now_price = int(data[-1][4])

            # high_track
            high = []
            for index in range(-30, 0):
                high.append(data[index][2])
            high.sort(reverse=True)
            high_track = float(high[0])

            # low_track
            low = []
            for index in range(-30, 0):
                low.append(data[index][3])
            low.sort()
            low_track = float(low[0])

            # interval_range
            interval_range = (high_track - low_track) / (high_track + low_track)

            # current position qty of the symbol
            position_details = self.get_position_details()

            if position_details is None:
                continue

            position_qty = int(position_details['currentQty'])

            order_flag = 0
            if position_qty > 0:
                order_flag = 1
            elif position_qty < 0:
                order_flag = -1

            if order_flag == 1 and now_price > high_track and self.create_sell_limit_order(now_price):
                order_flag = 0
            elif order_flag == -1 and now_price < low_track and self.create_buy_limit_order(now_price):
                order_flag = 0

            if interval_range < self.valve and order_flag == 0:
                if now_price > high_track:
                    self.create_sell_limit_order(now_price)
                elif now_price < low_track:
                    self.create_buy_limit_order(now_price)


class Webserver(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(bytes('{"test": 1}', "utf-8"))


if __name__ == "__main__":
    shock = Shock()
    t1 = threading.Thread(target=shock.loop)
    t1.start()
    webServer = HTTPServer(('localhost', 8080), Webserver)
    webServer.serve_forever()
