#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import time

from kumex.client import Trade, Market


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

    def error(self, error):
        time.sleep(self.resolution)

    def create_sell_limit_order(self, price):
        try:
            order = shock.trade.create_limit_order(shock.symbol, 'sell', self.leverage, self.size, price,
                                                   timeInForce='IOC')
            while shock.trade.get_order_details(order['orderId']).get('isActive'):
                print('waiting for order execution...')
        except BaseException as e:
            print('sell order execution failed!')

            self.error(e)

            return False

        print('sell order executed', 'order id =', order['orderId'])

        return True

    def create_buy_limit_order(self, price):
        try:
            order = shock.trade.create_limit_order(shock.symbol, 'buy', self.leverage, self.size, price,
                                                   timeInForce='IOC')
            while shock.trade.get_order_details(order['orderId']).get('isActive'):
                print('waiting for order execution...')
        except BaseException as e:
            print('buy order execution failed!')

            self.error(e)

            return False

        print('buy order executed', 'order id =', order['orderId'])

        return True


if __name__ == "__main__":
    shock = Shock()

    while 1:
        time_to = int(time.time() * 1000)
        time_from = time_to - shock.resolution * 60 * 35 * 1000
        try:
            data = shock.market.get_kline_data(shock.symbol, shock.resolution, time_from, time_to)
        except BaseException as e:
            print('kline retrieval failed!')
            shock.error(e)
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
        position_details = shock.trade.get_position_details(shock.symbol)
        position_qty = int(position_details['currentQty'])

        order_flag = 0
        if position_qty > 0:
            order_flag = 1
        elif position_qty < 0:
            order_flag = -1
            position_qty = abs(position_qty)

        if order_flag == 1 and now_price > high_track and shock.create_sell_limit_order(now_price):
            order_flag = 0
        elif order_flag == -1 and now_price < low_track and shock.create_buy_limit_order(now_price):
            order_flag = 0

        if interval_range < shock.valve and order_flag == 0:
            if now_price > high_track:
                shock.create_sell_limit_order(now_price)
            elif now_price < low_track:
                shock.create_buy_limit_order(now_price)
