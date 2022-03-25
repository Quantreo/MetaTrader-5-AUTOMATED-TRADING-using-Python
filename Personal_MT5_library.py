import MetaTrader5 as mt5
import pandas as pd
import numpy as np

from datetime import datetime


class MT5:
    max_price = dict()
    min_price = dict()
    summary = None
    
    def get_ticks(symbol, number_of_data = 10000):
        # Compute now date
        from_date = datetime.now()

        # Extract n Ticks before now
        ticks = mt5.copy_ticks_from(symbol, from_date, number_of_data,  mt5.COPY_TICKS_ALL)

        # Transform Tuple into a DataFrame
        df_ticks = pd.DataFrame(ticks)

        # Convert number format of the date into date format
        df_ticks["time"] = pd.to_datetime(df_ticks["time"], unit="s")

        df_ticks = df_ticks.set_index("time")

        return df_ticks
    
    
    def get_rates(symbol, number_of_data = 10000, timeframe=mt5.TIMEFRAME_D1):
        # Compute now date
        from_date = datetime.now()

        # Extract n Ticks before now
        rates = mt5.copy_rates_from(symbol, timeframe, from_date, number_of_data)


        # Transform Tuple into a DataFrame
        df_rates = pd.DataFrame(rates)

        # Convert number format of the date into date format
        df_rates["time"] = pd.to_datetime(df_rates["time"], unit="s")

        df_rates = df_rates.set_index("time")

        return df_rates
    
    def risk_reward_threshold(symbol, buy=True, risk=0.01, reward=0.02):
    
        # Extract the leverage
        leverage = mt5.account_info().leverage

        # Compute the price
        price = mt5.symbol_info(symbol).ask
        
        # Extract the number of decimals
        nb_decimal = str(price)[::-1].find(".")


        # Compute the variations in percentage
        var_down = risk/leverage
        var_up = reward/leverage


        # Find the TP and SL threshold in absolute price
        if buy:
            price = mt5.symbol_info(symbol).ask
            
            # Compute the variations in absolute price
            price_var_down = var_down*price
            price_var_up = var_up * price
            
            tp = np.round(price + price_var_up, nb_decimal)
            sl = np.round(price - price_var_down, nb_decimal)
        
        else:
            
            price = mt5.symbol_info(symbol).bid
            
            # Compute the variations in absolute price
            price_var_down = var_down*price
            price_var_up = var_up * price
            
            tp = np.round(price - price_var_up, nb_decimal)
            sl = np.round(price + price_var_down, nb_decimal)


        return tp, sl
    
    def find_filling_mode(symbol):
    
        for i in range(2):
            request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": mt5.symbol_info(symbol).volume_min,
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(symbol).ask,
            "type_filling": i,
            "type_time": mt5.ORDER_TIME_GTC}

            result = mt5.order_check(request)
            
            if result.comment == "Done":
                break

        return i
        
        
    def send_order(symbol, lot, buy, sell, id_position=None, pct_tp=0.02, pct_sl=0.01, comment=" No specific comment", magic=0):
    
        # Initialize the bound between MT5 and Python
        mt5.initialize()

        # Extract filling_mode
        filling_type = MT5.find_filling_mode(symbol)


        """ OPEN A TRADE """
        if buy and id_position==None:
            tp, sl = MT5.risk_reward_threshold(symbol, buy=True, risk=pct_sl, reward=pct_tp)
            
            request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(symbol).ask,
            "deviation": 10,
            "tp": tp,
            "sl": sl, 
            "magic": magic,
            "comment": comment,
            "type_filling": filling_type,
            "type_time": mt5.ORDER_TIME_GTC}

            result = mt5.order_send(request)
            
            print(mt5.symbol_info_tick(symbol).ask, tp, sl)
            return result

        if sell and id_position==None:
            tp, sl = MT5.risk_reward_threshold(symbol, buy=False, risk=pct_sl, reward=pct_tp)
            request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_SELL,
            "price": mt5.symbol_info_tick(symbol).bid,
            "deviation": 10,
            "tp": tp,
            "sl": sl, 
            "magic": magic,
            "comment": comment,
            "type_filling": filling_type,
            "type_time": mt5.ORDER_TIME_GTC}

            result = mt5.order_send(request)
            
            print(mt5.symbol_info_tick(symbol).bid, tp, sl)
            return result


        """ CLOSE A TRADE """
        if buy and id_position!=None:
            request = {
            "position": id_position,
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_SELL,
            "price": mt5.symbol_info_tick(symbol).bid,
            "deviation": 10,
            "magic": magic,
            "comment": comment,
            "type_filling": filling_type,
            "type_time": mt5.ORDER_TIME_GTC}

            result = mt5.order_send(request)
            return result

        if sell and id_position!=None:
            request = {
            "position": id_position,
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(symbol).ask,
            "deviation": 10,
            "magic": magic,
            "comment": comment,
            "type_filling": filling_type,
            "type_time": mt5.ORDER_TIME_GTC}

            result = mt5.order_send(request)
            return result

    def resume():
        """ Return the current positions. Position=0 --> Buy """    
        # Define the name of the columns that we will create
        colonnes = ["ticket", "position", "symbol", "volume", "magic", "profit", "price", "tp", "sl","trade_size"]

        # Go take the current open trades
        liste = mt5.positions_get()

        # Create a empty dataframe
        summary = pd.DataFrame()

        # Loop to add each row in dataframe
        for element in liste:
            element_pandas = pd.DataFrame([element.ticket, element.type, element.symbol, element.volume, element.magic,
                                           element.profit, element.price_open, element.tp,
                                           element.sl, mt5.symbol_info(element.symbol).trade_contract_size],
                                          index=colonnes).transpose()
            summary = pd.concat((summary, element_pandas), axis=0)

        try:
            summary["profit %"] = summary.profit / (summary.price * summary.trade_size * summary.volume)
            summary = summary.reset_index(drop=True)
        except:
            pass
        return summary
    
    
    def trailing_stop_loss():

        # Extract the current open positions
        MT5.summary = MT5.resume()

        # Verification: Is there any open position?
        if MT5.summary.shape[0] >0:
            for i in range(MT5.summary.shape[0]):

                # Extract information
                row = MT5.summary.iloc[i]
                symbol = row["symbol"]





                """ CASE 1: Change dynamicly the stop loss for a BUY ORDER """
                # Trailing stop loss for a buy order
                if row["position"] == 0:

                    if symbol not in MT5.max_price.keys():
                        MT5.max_price[symbol]=row["price"]

                    # Extract current price 
                    current_price = (mt5.symbol_info(symbol).ask + mt5.symbol_info(symbol).bid ) / 2

                    #Compute distance between current price an max price
                    from_sl_to_curent_price = current_price - row["sl"]
                    from_sl_to_max_price = MT5.max_price[symbol] - row["sl"]


                    # If current price is greater than preivous max price --> new max price
                    if current_price > MT5.max_price[symbol]:
                        MT5.max_price[symbol] = current_price


                    # Find the difference between the current minus max 
                    if from_sl_to_curent_price > from_sl_to_max_price:
                        difference = from_sl_to_curent_price - from_sl_to_max_price

                        # Set filling mode
                        filling_type = mt5.symbol_info(symbol).filling_mode

                        # Set the point
                        point = mt5.symbol_info(symbol).point

                        # Change the sl
                        request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": symbol,
                        "position": row["ticket"],
                        "volume": row["volume"],
                        "type": mt5.ORDER_TYPE_BUY,
                        "price": row["price"],
                        "sl": row["sl"] + difference,
                        "type_filling": filling_type,
                        "type_time": mt5.ORDER_TIME_GTC,
                        }

                        information = mt5.order_send(request)
                        print(information)


                """ CASE 2: Change dynamicly the stop loss for a SELL ORDER """
                # Trailing stop loss for a sell order
                if row["position"] == 1:

                    if symbol not in MT5.min_price.keys():
                        MT5.min_price[symbol]=row["price"]

                    # Extract current price 
                    current_price = (mt5.symbol_info(symbol).ask + mt5.symbol_info(symbol).bid ) / 2



                    #Compute distance between current price an max price
                    from_sl_to_curent_price = row["sl"] - current_price
                    from_sl_to_min_price = row["sl"] - MT5.min_price[symbol]

                     # If current price is greater than preivous max price --> new max price
                    if current_price < MT5.min_price[symbol]:
                        MT5.min_price[symbol] = current_price


                    # Find the difference between the current minus max 
                    if from_sl_to_curent_price > from_sl_to_min_price:
                        difference = from_sl_to_curent_price - from_sl_to_min_price 

                        # Set filling mode
                        filling_type = mt5.symbol_info(symbol).filling_mode

                        # Set the point
                        point = mt5.symbol_info(symbol).point

                        # Change the sl
                        request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": symbol,
                        "position": row["ticket"],
                        "volume": row["volume"],
                        "type": mt5.ORDER_TYPE_SELL,
                        "price": row["price"],
                        "sl": row["sl"] - difference,
                        "type_filling": filling_type,
                        "type_time": mt5.ORDER_TIME_GTC,
                        }


                        information = mt5.order_send(request)
                        print(information)
                        
    def verif_tsl():

        #print("MAX", MT5.max_price)

        #print("MIN", MT5.min_price)

        if len(MT5.summary)>0:
            buy_open_positions = MT5.summary.loc[MT5.summary["position"]==0]["symbol"]
            sell_open_positions = MT5.summary.loc[MT5.summary["position"]==0]["symbol"]
        else:
            buy_open_positions = []
            sell_open_positions = []

        """ IF YOU CLOSE ONE OF YOUR POSITION YOU NEED TO DELETE THE PRICE IN THE MAX AND MIN PRICES DICTIONNARIES"""
        if len(MT5.max_price) != len(buy_open_positions) and len(buy_open_positions) >0:
            symbol_to_delete = []

            for symbol in MT5.max_price.keys():

                if symbol not in list(buy_open_positions):
                    symbol_to_delete.append(symbol)

            for symbol in symbol_to_delete:
                del MT5.max_price[symbol]

        if len(MT5.min_price) != len(sell_open_positions) and len(sell_open_positions) >0:
            symbol_to_delete = []

            for symbol in MT5.min_price.keys():

                if symbol not in list(sell_open_positions):
                    symbol_to_delete.append(symbol)

            for symbol in symbol_to_delete:
                del MT5.min_price[symbol]

        if len(buy_open_positions) == 0:
            MT5.max_price={}

        if len(sell_open_positions) == 0:
            MT5.min_price={}
            
            
    def run(symbol, buy, sell, lot, pct_tp=0.02, pct_sl=0.01, comment="", magic=23400):

            # Initialize the connection
            mt5.initialize()

            # Choose your  symbol
            print("------------------------------------------------------------------")
            print("Date: ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "\tSYMBOL:", symbol)

            # Initialize the device
            ouvertures = MT5.resume()

            # Buy or sell
            print(f"BUY: {buy} \t  SELL: {sell}")

            """ Close trade eventually """
            # Extraction type trade
            try:
                position = ouvertures.loc[ouvertures["symbol"] == symbol].values[0][1]

                identifier = ouvertures.loc[ouvertures["symbol"] == symbol].values[0][0]
            except:
                position = None
                identifier = None

            if position!=None:
                print(f"POSITION: {position} \t ID: {identifier}")

            # Verif trades
            if buy == True and position == 0:
                buy = False

            elif buy == False and position == 0:
                before = mt5.account_info().balance
                res = MT5.send_order(symbol, lot, True, False, id_position=identifier,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=0)
                after = mt5.account_info().balance

                print(f"CLOSE BUY POSITION: {res.comment}")
                pct = np.round(100*(after-before)/before, 3)

                if res.comment != "Request executed":
                    print("WARNINGS", res.comment)



            elif sell == True and position == 1:
                sell = False

            elif sell == False and position == 1:
                before = mt5.account_info().balance
                res = MT5.send_order(symbol, lot, False, True, id_position=identifier,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=0)
                print(f"CLOSE SELL POSITION: {res.comment}")
                after = mt5.account_info().balance

                pct = np.round(100*(after-before)/before, 3)
                if res.comment != "Request executed":
                    print("WARNINGS", res.comment)


            else:
                pass

            """ Buy or Sell """
            if buy == True:
                res =  MT5.send_order(symbol, lot, True, False, id_position=None,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=0)
                print(f"OPEN BUY POSITION: {res.comment}")
                if res.comment != "Request executed":
                    print("WARNINGS", res.comment)

            if sell == True:
                res = MT5.send_order(symbol, lot, False, True, id_position=None,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=0)
                print(f"OPEN SELL POSITION: {res.comment}")
                if res.comment != "Request executed":
                    print("WARNINGS",  res.comment)
            print("------------------------------------------------------------------")

