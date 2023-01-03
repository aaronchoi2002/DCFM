# -*- coding: utf-8 -*-
"""
Created on Mon Jan  2 19:04:05 2023

@author: USER
"""

import pandas as pd
from bs4 import BeautifulSoup
import requests
import streamlit as st 
from urllib.request import urlopen
import json
import numpy as np
import plotly.graph_objects as go
import yfinance as yf

fmp_api_key = "e3e1ef68f4575bca8a430996a4e11ed1"
headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36'}
df_bgm = pd.DataFrame()

st.title('Discount Cash Flow Model')

stock = st.text_input("Enter ticker here" , value="AAPL")

#get stock basic information 
def Get_Stock(Stock_code): 

    response = urlopen(f"https://financialmodelingprep.com/api/v3/quote/{Stock_code.upper()}?apikey={fmp_api_key}")
    Stock = response.read().decode("utf-8")
    Stock = json.loads(Stock)
    Stock =pd.json_normalize(Stock).T
    Price = round(float(Stock.loc["price"].fillna(0)),2)
    Name = Stock.loc["name"].iloc[0]
    PE = round(float(Stock.loc["pe"].fillna(0)),2)
    Share_out_standing = (int(Stock.loc["sharesOutstanding"]))
    return[Price, Name, PE, Share_out_standing]

#get grown rate 
def grown_rate(Stock_code): 
    response = requests.get("https://finance.yahoo.com/quote/{}/analysis?p={}".format(Stock_code,Stock_code),headers=headers)
    soup = BeautifulSoup(response.text,"html.parser")
    if (len(soup.find_all(class_="Ta(end) Py(10px)"))<16):
      grown = 0
    else:
      grown = soup.find_all(class_="Ta(end) Py(10px)")[16].text
      grown = float(grown.replace("%", "")) if (grown != 'N/A') else 0
    return(grown)

#get wacc
def Get_Stock_DCFM_data(Stock_code): 
    response = urlopen(f"https://financialmodelingprep.com/api/v4/advanced_discounted_cash_flow?symbol={Stock_code.upper()}&apikey={fmp_api_key}")
    Stock = response.read().decode("utf-8")
    Stock = json.loads(Stock)
    Stock =pd.json_normalize(Stock).T
    wacc = round(Stock.loc["wacc"].iloc[0],2) if type(Stock.loc["wacc"].iloc[0]) == float else 0.0
    return wacc

# get Free cash flow 
def Get_Free_Cash_Flow(Stock_code): 
    response = urlopen(f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{Stock_code.upper()}?apikey={fmp_api_key}")
    Stock = response.read().decode("utf-8")
    Stock = json.loads(Stock)
    Stock =pd.json_normalize(Stock).T
    date = Stock.loc["date"].iloc[0]
    Current_FCFP = round(Stock.loc["freeCashFlow"].iloc[0],2)
    date= int(date.split("-")[0])
    return[Current_FCFP,date]

Current_FCFP = Get_Free_Cash_Flow(stock)[0]
date = Get_Free_Cash_Flow(stock)[1]
wacc = Get_Stock_DCFM_data(stock)
grown = grown_rate(stock)
price = Get_Stock(stock)[0]
name = Get_Stock(stock)[1]
pe = Get_Stock(stock)[2]
share_outstanding = Get_Stock(stock)[3]

# Display basic stock information
st.code(f"Name: {name}")
col1, col2, col3, col4= st.columns([1.5,0.8,1,0.8])
with col1:
    st.code(f"Price: {price}")
with col2:
    st.code(f"Grown: {grown}")
with col3:
    st.code(f"P/E Ratio: {pe}")
with col4:
    st.code(f"WACC: {wacc}")

min_value = pe*0.3
max_value = pe
value = pe
step = pe*0.05
Margin_of_safty = st.slider("Margin of safty (P/E)", min_value=min_value, max_value=max_value, value=value, step=step)   
    
#Discount Cast Flow Model     
dcf_df ={"Income statment number":["Year","Free Cash Flow(m)","Discount Factor", "Present Value(m)"]}
dcf_df = pd.DataFrame(dcf_df).set_index("Income statment number")
for i in range(0,11):
    dcf_df[i] = "N/A"
    dcf_df.loc["Year",i] = str(date +i)
    dcf_df.loc["Free Cash Flow(m)",i] = round(Current_FCFP*(1+(grown/100))**i,0)
    dcf_df.loc["Discount Factor",i] = round((1+wacc/100)**i,4)
    dcf_df.loc["Present Value(m)",i] = round(dcf_df.loc["Free Cash Flow(m)",i]/dcf_df.loc["Discount Factor",i],0)

terminal_value = dcf_df.loc["Free Cash Flow(m)",10]*pe
pv_terminal_value = terminal_value/dcf_df.loc["Discount Factor",10]
equity_value = round(sum(dcf_df.loc["Present Value(m)",1:])+pv_terminal_value,0)
intrinsic_value = equity_value/share_outstanding

#Margin of Safty
mos_terminal_value = dcf_df.loc["Free Cash Flow(m)",10]*Margin_of_safty
mos_pv_terminal_value = mos_terminal_value/dcf_df.loc["Discount Factor",10]
mos_equity_value = round(sum(dcf_df.loc["Present Value(m)",1:])+mos_pv_terminal_value,0)
mos_intrinsic_value = mos_equity_value/share_outstanding

col1, col2 = st.columns([1,1])
with col1:
    st.code(f"Equity Value: {equity_value:,}")
with col2:
    st.code(f"Share_Outstanding: {share_outstanding:,}")

st.code(f"Intrinsic Value: {round(intrinsic_value,2)}")
st.code(f"Margin of safty: {round(mos_intrinsic_value,2)}, P/E discount:{round(1-(Margin_of_safty/pe),2)}")

#Chart
  #Get Price from Yahoo
stock_price = yf.download(stock, period="3y")
stock_price.reset_index(inplace=True)
fig = go.Figure()
fig.add_trace(go.Candlestick(x=stock_price["Date"], open=stock_price["Open"], high=stock_price["High"], low=stock_price["Low"], close=stock_price["Close"]) )
fig.add_hline(y=intrinsic_value, line_dash="dot" , annotation_text=f"Intrinsic Value: {round(intrinsic_value,2)}")
fig.add_hline(y=mos_intrinsic_value , annotation_text=f"Margin_of_safty: {round(mos_intrinsic_value,2)}")
st.plotly_chart(fig)

#Display table 
Display_dcf = dcf_df.copy()
Display_dcf.loc["Free Cash Flow(m)",:] = Display_dcf.loc["Free Cash Flow(m)",:]/1000000
Display_dcf.loc["Present Value(m)",:] = Display_dcf.loc["Present Value(m)",:]/1000000
Display_dcf = Display_dcf.T
Display_dcf["Free Cash Flow(m)"] = Display_dcf["Free Cash Flow(m)"].apply(np.ceil)
Display_dcf["Present Value(m)"] = Display_dcf["Free Cash Flow(m)"].apply(np.ceil)
Display_dcf = Display_dcf.T
st.dataframe(data=Display_dcf)
st.text("*m = milion")


#historial PE
Stock_code = stock
response = urlopen("https://financialmodelingprep.com/api/v3/ratios/" + Stock_code.upper() + "?limit=40&apikey=e3e1ef68f4575bca8a430996a4e11ed1")
Stock = response.read().decode("utf-8")
Stock = json.loads(Stock)
Stock = pd.json_normalize(Stock)
PEs = Stock[["date","priceEarningsRatio"]].iloc[0:10]
st.sidebar.dataframe(data=PEs)