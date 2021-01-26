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

    def connection_error(self):
        print('connection error, sleeping for a bit...')
        time.sleep(self.resolution)


if __name__ == "__main__":
    shock = Shock()

    while 1:
        time_to = int(time.time() * 1000)
        time_from = time_to - shock.resolution * 60 * 35 * 1000
        try:
            data = shock.market.get_kline_data(shock.symbol, shock.resolution, time_from, time_to)
        except ConnectionError as e:
            shock.connection_error()
            continue

        now_price = int(data[-1][4])
        print('closed price =', now_price)

        # high_track
        high = []
        for index in range(-30, 0):
            high.append(data[index][2])
        high.sort(reverse=True)
        high_track = float(high[0])
        print('high_track =', high_track)

        # low_track
        low = []
        for index in range(-30, 0):
            low.append(data[index][3])
        low.sort()
        low_track = float(low[0])
        print('low_track =', low_track)

        # interval_range
        interval_range = (high_track - low_track) / (high_track + low_track)
        print('interval_range =', interval_range)

        order_flag = 0
        # current position qty of the symbol
        position_details = shock.trade.get_position_details(shock.symbol)
        position_qty = int(position_details['currentQty'])
        print('current position qty of the symbol =', position_qty)
        if position_qty > 0:
            order_flag = 1
        elif position_qty < 0:
            order_flag = -1
            position_qty = abs(position_qty)

        if order_flag == 1 and now_price > high_track - .5:
            order = shock.trade.create_limit_order(shock.symbol, 'sell', position_details['realLeverage'],
                                                   position_qty, now_price, cancel_after='5')

            while shock.trade.get_order_details(order['orderId']).get('isActive'):
                print('waiting for order execution...')
            print('order_flag == 1,order id =', order['orderId'])
            order_flag = 0
        elif order_flag == -1 and now_price < low_track + .5:
            order = shock.trade.create_limit_order(shock.symbol, 'buy', position_details['realLeverage'],
                                                   position_qty, now_price, cancel_after='5')

            while shock.trade.get_order_details(order['orderId']).get('isActive'):
                print('waiting for order execution...')
            print('order_flag == -1,order id =', order['orderId'])
            order_flag = 0

        if interval_range < shock.valve and order_flag == 0:
            if now_price > high_track:
                order = shock.trade.create_limit_order(shock.symbol, 'sell', shock.leverage,
                                                       shock.size, now_price, cancel_after='5')

                while shock.trade.get_order_details(order['orderId']).get('isActive'):
                    print('waiting for order execution...')
                print('now price < high track,sell order id =', order['orderId'])
                order_flag = -1
            elif now_price < low_track:
                order = shock.trade.create_limit_order(shock.symbol, 'buy', shock.leverage,
                                                       shock.size, now_price, cancel_after='5')

                while shock.trade.get_order_details(order['orderId']).get('isActive'):
                    print('waiting for order execution...')
                print('now price > high track,buy order id =', order['orderId'])
                order_flag = 1
