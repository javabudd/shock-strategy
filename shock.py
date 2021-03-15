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
        self.stopLossThreshold = float(config['stop_loss_threshold'])
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

        if trade is not None and 'orderId' in trade:
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

        if trade is not None and 'orderId' in trade:
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

        if trade is not None and 'orderId' in trade:
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

        if trade is not None and 'orderId' in trade:
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

    @staticmethod
    def is_three_line_strike(kline_data):
        first_candle_low = kline_data[-4][3]
        second_candle_low = kline_data[-3][3]
        third_candle_low = kline_data[-2][3]
        third_candle_high = kline_data[-2][2]
        fourth_candle_low = kline_data[-1][3]

        return fourth_candle_low < third_candle_low < second_candle_low < first_candle_low \
               and now_price > third_candle_high

    @staticmethod
    def is_two_block_gapping(kline_data):
        first_candle_high = kline_data[-4][2]
        second_candle_high = kline_data[-3][2]
        second_candle_low = kline_data[-3][3]
        third_candle_low = kline_data[-2][3]
        third_candle_high = kline_data[-2][2]
        fourth_candle_low = kline_data[-1][3]
        gap_met = second_candle_low - third_candle_high > second_candle_low * .02

        return first_candle_high > second_candle_high and third_candle_high < second_candle_low \
               and gap_met and fourth_candle_low < third_candle_low


if __name__ == "__main__":
    shock = Shock()
    logging.basicConfig(level=logging.INFO)
    logging.info('Starting trader...')
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

        if order_flag == 1:
            high = []
            for index in data:
                high.append(index[2])

            high.sort(reverse=True)
            high_track = float(high[0])

            if now_price <= purchase_price:
                if 1 - (now_price / purchase_price) >= shock.stopLossThreshold:
                    shock.create_sell_market_order()
            elif now_price > high_track:
                shock.create_sell_market_order()
        elif order_flag == -1:
            low = []
            for index in data:
                low.append(index[3])

            low.sort()
            low_track = float(low[0])

            if now_price >= purchase_price:
                if 1 - (purchase_price / now_price) >= shock.stopLossThreshold:
                    shock.create_buy_market_order()
            elif now_price < low_track:
                shock.create_buy_market_order()
        elif order_flag == 0:
            if shock.is_three_line_strike(data):
                shock.create_buy_market_order()
            elif shock.is_two_block_gapping(data):
                shock.create_sell_market_order()
