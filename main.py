import models
import yfinance
from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from database import SessionLocal, engine
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models import Stock

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

class StockRequest(BaseModel):
    symbol: str

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@app.get("/")
def dashboard(request: Request, avg_volume = None, market_cap = None, dividend_yield = None, percent_change = None, ma50 = None, ma200 = None, forward_pe = None, forward_eps = None, db: Session = Depends(get_db)):
    """
    displays the stock screener dashboard / homepage
    """

    stocks = db.query(Stock)

    if avg_volume:
        stocks = stocks.filter(Stock.avg_volume > avg_volume)

    if market_cap:
        stocks = stocks.filter(Stock.market_cap > market_cap)

    if dividend_yield:
        stocks = stocks.filter(Stock.dividend_yield > dividend_yield)

    if percent_change:
        stocks = stocks.filter(Stock.percent_change> percent_change)

    if forward_pe:
        stocks = stocks.filter(Stock.forward_pe < forward_pe)

    if forward_eps:
        stocks = stocks.filter(Stock.forward_eps > forward_eps)
    
    if ma50:
        stocks = stocks.filter(Stock.price > Stock.ma50)

    if ma200:
        stocks = stocks.filter(Stock.price > Stock.ma200)

    stocks = stocks.all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stocks": stocks,
        "dividend_yield": dividend_yield,
        "percent_change": percent_change,
        "forward_pe": forward_pe,
        "forward_eps": forward_eps,
        "ma50": ma50,
        "ma200": ma200,
        "market_cap": market_cap,
        "avg_volume": avg_volume
        
    })

def fetch_stock_data(id: int):
    db = SessionLocal()
    stock = db.query(Stock).filter(Stock.id == id).first()

    yahoo_data = yfinance.Ticker(stock.symbol)

    if yahoo_data.info['twoHundredDayAverage'] is not None:
        stock.ma200 = yahoo_data.info['twoHundredDayAverage']

    if yahoo_data.info['fiftyDayAverage'] is not None:
        stock.ma50 = yahoo_data.info['fiftyDayAverage']

    if yahoo_data.info['currentPrice'] is not None:
        stock.price = yahoo_data.info['currentPrice']

    if yahoo_data.info['previousClose'] is not None:
        stock.previous_close = yahoo_data.info['previousClose']

    if yahoo_data.info['averageVolume'] is not None:
        stock.avg_volume = yahoo_data.info['averageVolume'] / 1000000

    if yahoo_data.info['marketCap'] is not None:
        stock.market_cap = yahoo_data.info['marketCap'] / 10000000000

    if yahoo_data.info['forwardPE'] is not None:
        stock.forward_pe = yahoo_data.info['forwardPE']

    if yahoo_data.info['forwardEps'] is not None:
        stock.forward_eps = yahoo_data.info['forwardEps']

    if yahoo_data.info['dividendYield'] is not None:
        stock.dividend_yield = yahoo_data.info['dividendYield'] * 100

    stock.percent_change = ((yahoo_data.info['currentPrice'] / yahoo_data.info['previousClose']) - 1) * 100
    

    db.add(stock)
    db.commit()

@app.post("/stock")
async def create_stock(stock_request: StockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    created a stock and stores it in the database
    """

    stock = Stock()
    stock.symbol = stock_request.symbol

    db.add(stock)
    db.commit()

    background_tasks.add_task(fetch_stock_data, stock.id)

    return {
        "code": "success",
        "message": "stock created"
    }
