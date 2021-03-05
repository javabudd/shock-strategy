#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import logging
import time

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
        message = message + ': ' + getattr(error, 'message', repr(error))
        logging.error(message)
        self.slack_message(message)
        time.sleep(self.resolution)

    def create_sell_limit_order(self, price):
        try:
            trade = shock.trade.create_limit_order(shock.symbol, 'sell', self.leverage, self.size, price,
                                                   timeInForce='IOC')
        except BaseException as e:
            self.error(e, 'limit sell order execution failed!')

            return None

        if trade is not None:
            self.slack_message('limit sell order executed: ' + 'order id = ' + trade['orderId'])

            return trade['orderId']

        return None

    def create_sell_market_order(self):
        try:
            trade = shock.trade.create_market_order(shock.symbol, 'sell', self.leverage, timeInForce='IOC',
                                                    size=self.size)
        except BaseException as e:
            self.error(e, 'market sell order execution failed!')

            return None

        if trade is not None:
            self.slack_message('market sell order executed: ' + 'order id = ' + trade['orderId'])

            return trade['orderId']

        return None

    def create_buy_limit_order(self, price):
        try:
            trade = shock.trade.create_limit_order(shock.symbol, 'buy', self.leverage, self.size, price,
                                                   timeInForce='IOC')
        except BaseException as e:
            self.error(e, 'limit buy order execution failed!')

            return None

        if trade is not None:
            self.slack_message('limit buy order executed: ' + 'order id = ' + trade['orderId'])

            return trade['orderId']

        return None

    def create_buy_market_order(self):
        try:
            trade = shock.trade.create_market_order(shock.symbol, 'buy', self.leverage, timeInForce='IOC',
                                                    size=self.size)
        except BaseException as e:
            self.error(e, 'market buy order execution failed!')

            return None

        if trade is not None:
            self.slack_message('market buy order executed: ' + 'order id = ' + trade['orderId'])

            return trade['orderId']

        return None

    def get_order_by_id(self, trade_order_id):
        try:
            trade = shock.trade.get_order_details(trade_order_id)
        except BaseException as e:
            self.error(e, 'order retrieval failed!')

            return None

        return trade

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
        logging.info(message)
        self.slack.chat_postMessage(channel=self.slack_channel, text=message)


if __name__ == "__main__":
    shock = Shock()
    logging.basicConfig(level=logging.INFO)
    logging.info('Starting trader...')
    loss_threshold = .005
    purchase_price = 0.0

    while 1:
        time_to = int(time.time() * 1000)
        time_from = time_to - shock.resolution * 60 * 35 * 1000
        data = shock.get_kline_data(time_from, time_to)

        if data is None:
            logging.error('Failed retrieving kline data')
            continue

        now_price = float(data[-1][4])

        if now_price == 0:
            logging.error('Failed retrieving corrupted')
            continue

        high = []
        low = []
        data.pop(len(data) - 1)
        for index in data:
            high.append(index[2])
            low.append(index[3])

        if len(high) == 0:
            logging.error('Failed to get a high range')
            continue

        if len(low) == 0:
            logging.error('Failed to get a low range')
            continue

        high.sort(reverse=True)
        high_track = float(high[0])

        low.sort()
        low_track = float(low[0])

        # interval_range
        interval_range = (high_track - low_track) / (high_track + low_track)

        # current position qty of the symbol
        position_details = shock.get_position_details()

        if position_details is None:
            logging.error('Failed retrieving position details')
            continue

        position_qty = int(position_details['currentQty'])

        order_flag = 0
        if position_qty > 0:
            order_flag = 1
            purchase_price = float(position_details['avgEntryPrice'])
        elif position_qty < 0:
            order_flag = -1
            purchase_price = float(position_details['avgEntryPrice'])

        within_range = interval_range <= shock.valve
        message_str = 'Interval Range: ' + str(interval_range)

        if within_range:
            logging.info(message_str)
        else:
            logging.warning(message_str)

        logging.info('Close: ' + str(now_price))
        logging.info('High: ' + str(high_track))
        logging.info('Low: ' + str(low_track))

        if within_range:
            if order_flag != 0:
                if purchase_price == 0.0:
                    logging.error('Failed retrieving last purchase price')
                    continue

                # future close
                if order_flag == 1:
                    if now_price < purchase_price:
                        if 1 - (now_price / purchase_price) >= loss_threshold:
                            shock.create_sell_market_order()
                            order_flag = 0
                    elif now_price > high_track:
                        shock.create_sell_market_order()
                        order_flag = 0
                elif order_flag == -1:
                    if now_price > purchase_price:
                        if 1 - (purchase_price / now_price) >= loss_threshold:
                            shock.create_buy_market_order()
                            order_flag = 0
                    elif now_price < low_track:
                        shock.create_buy_market_order()
                        order_flag = 0

            # future open
            if order_flag == 0:
                if now_price > high_track:
                    order = shock.create_sell_limit_order(now_price)
                    if order is not None:
                        time.sleep(5)
                elif now_price < low_track:
                    order = shock.create_buy_limit_order(now_price)
                    if order is not None:
                        time.sleep(5)
