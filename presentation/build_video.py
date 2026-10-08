"""Create a captioned project presentation from the actual sample CSVs."""
from pathlib import Path
import sys
import subprocess
import math

from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from portfolio import analyze_holdings, analyze_history

OUT = ROOT / 'presentation'
W, H = 1280, 720
BG, PANEL, TEXT, MUTED, TEAL, BLUE = '#101B30', '#1B2A43', '#F3F7FC', '#A8B8D0', '#37D4BD', '#66A8FF'
FONT = '/System/Library/Fonts/Helvetica.ttc'

def font(size):
    return ImageFont.truetype(FONT, size)

def text(draw, value, xy, size=24, color=TEXT):
    draw.text(xy, value, font=font(size), fill=color)

def wrap(draw, value, width, size):
    result, current = [], ''
    for word in value.split():
        proposal = (current + ' ' + word).strip()
        if draw.textlength(proposal, font=font(size)) > width and current:
            result.append(current)
            current = word
        else:
            current = proposal
    if current:
        result.append(current)
    return result

def paragraph(draw, value, x, y, width=1120, size=27, color=MUTED):
    for line in wrap(draw, value, width, size):
        text(draw, line, (x,y), size, color)
        y += size + 12
    return y

def base(index, title, kicker):
    im = Image.new('RGB',(W,H),BG)
    draw = ImageDraw.Draw(im)
    draw.rectangle((0,0,W,8),fill=TEAL)
    text(draw,'RAMADHAR MISHRA  /  TRAINING PROJECT', (64,38),18,MUTED)
    text(draw,kicker.upper(),(64,91),20,TEAL)
    text(draw,title,(64,132),44)
    draw.line((64,641,1216,641),fill=PANEL,width=2)
    text(draw,'Stock Portfolio Analyzer  |  Python + Streamlit',(64,666),18,MUTED)
    text(draw,f'{index:02d} / 11',(1130,666),18,TEAL)
    return im,draw

holdings = analyze_holdings(pd.read_csv(ROOT/'data/sample_portfolio.csv'))
prices, summary = analyze_history(pd.read_csv(ROOT/'data/sample_prices.csv'))
value, cost = holdings.market_value.sum(), holdings.cost_basis.sum()
gain = value-cost
slides=[]
script=[]

def save(im, title, duration, caption):
    path=OUT/'slides'/f'{len(slides)+1:02d}.png'
    im.save(path)
    slides.append((path,duration))
    script.append(f'{len(slides):02d}. {title} ({duration} seconds)\n{caption}\n')

im,d=base(1,'Stock Portfolio Analyzer','Project presentation')
paragraph(d,'Turn uploaded stock CSVs into clear portfolio insights.',64,220,size=34,color=TEXT)
text(d,'Presented by Ramadhar Mishra',(64,317),30,TEAL)
for i,label in enumerate(['CSV upload','Portfolio metrics','Interactive charts','Validated analysis']):
    x=64+i*294
    d.rounded_rectangle((x,408,x+275,490),radius=14,fill=PANEL)
    text(d,label,(x+17,437),23)
paragraph(d,'A working Python data application developed with an AI-assisted workflow.',64,539,size=26)
save(im,'Introduction',14,'I am Ramadhar Mishra. My project is a Stock Portfolio Analyzer built with Python and Streamlit. It converts uploaded CSV datasets into portfolio metrics and visual analysis.')

im,d=base(2,'The problem and project goal','01 / Purpose')
y=220
for title,body in [('Problem','Stock information in CSV files is difficult to compare quickly.'),('Goal','Calculate holdings value, unrealized gains, and allocation in one place.'),('Outcome','Provide a usable dashboard with uploads, filters, charts, and exports.')]:
    text(d,title,(64,y),29,TEAL)
    paragraph(d,body,260,y,width=935,size=28)
    y+=120
save(im,'Purpose',15,'The goal is to make stock data easier to understand. Users can upload holdings or price history and immediately explore useful metrics and charts.')

im,d=base(3,'Two types of stock data','02 / CSV input')
for x,title,fields,body in [(64,'Portfolio holdings',['ticker, shares','average_cost, current_price','Optional: sector, previous_close'],'Analyze current open positions and separate purchase lots.'),(652,'Price history',['date, ticker, close','One closing price per date','Example date: 2025-01-02'],'Analyze price movements over the selected period.')]:
    d.rounded_rectangle((x,220,x+564,547),radius=18,fill=PANEL)
    text(d,title,(x+25,247),30,TEAL)
    for j,line in enumerate(fields): text(d,line,(x+25,305+j*43),25)
    paragraph(d,body,x+25,452,width=510,size=24)
paragraph(d,'The sample dataset contains Apple, Tesla, Google, and Salesforce. All sample prices are synthetic.',64,576,size=23)
save(im,'CSV formats',18,'The application supports two CSV formats. Holdings need ticker, shares, purchase cost per share, and current price. Price history needs date, ticker, and close. The demo contains Apple, Tesla, Google, and Salesforce with synthetic prices.')

im,d=base(4,'From upload to insight','03 / Application workflow')
steps=[('1','Upload CSV','Choose the dataset type'),('2','Map columns','Match your file headers'),('3','Validate data','Check values and dates'),('4','Analyze & export','Filter, chart, download')]
for i,(num,title,body) in enumerate(steps):
    x=64+i*294
    d.rounded_rectangle((x,255,x+270,471),radius=16,fill=PANEL)
    text(d,num,(x+22,279),44,TEAL)
    text(d,title,(x+22,347),25)
    paragraph(d,body,x+22,393,width=226,size=22)
paragraph(d,'CSV options support alternate delimiters and encodings. Ticker selections update the analysis.',64,533,size=28)
save(im,'Workflow',15,'First, choose holdings or history and upload a CSV. Map any custom header names, then the app validates the data. Use ticker filters to focus the analysis, inspect charts, and download the results.')

im,d=base(5,'Portfolio overview: calculated results','04 / Sample walkthrough')
metrics=[('Market value',f'USD {value:,.2f}'),('Invested cost',f'USD {cost:,.2f}'),('Unrealized gain',f'USD {gain:,.2f}'),('Gain vs. cost',f'{gain/cost*100:.2f}%')]
for i,(label,amount) in enumerate(metrics):
    x=64+i*294
    d.rounded_rectangle((x,221,x+274,329),radius=14,fill=PANEL)
    text(d,label,(x+17,241),21,MUTED)
    text(d,amount,(x+17,279),27,TEAL)
headers=['Stock','Shares','Purchase cost/share','Uploaded price','Market value']
xs=[85,295,475,775,1020]
for x,label in zip(xs,headers): text(d,label,(x,372),21,MUTED)
for j,row in enumerate(holdings.itertuples()):
    yy=414+j*43
    for x,v in zip(xs,[row.ticker,f'{row.shares:g}',f'{row.average_cost:.2f}',f'{row.current_price:.2f}',f'{row.market_value:,.2f}']): text(d,v,(x,yy),24)
text(d,'Actual calculations from the synthetic sample CSV; uploaded prices are not live quotes.',(64,604),21,MUTED)
save(im,'Sample portfolio metrics',18,f'The sample portfolio has a value of {value:,.2f} dollars and purchase cost of {cost:,.2f} dollars. Unrealized gain is {gain:,.2f} dollars, or {gain/cost*100:.2f} percent relative to cost. These values are calculated from the actual synthetic sample CSV.')

im,d=base(6,'Allocation and gain / loss','05 / Visual analysis')
left=holdings.sort_values('market_value',ascending=False)
text(d,'Portfolio weight by stock',(64,215),27,TEAL)
for i,row in enumerate(left.itertuples()):
    y=271+i*68
    text(d,row.ticker,(64,y),23)
    width=int(row.market_value/value*100*9)
    d.rounded_rectangle((160,y,160+width,y+30),radius=5,fill=BLUE)
    text(d,f'{row.market_value/value*100:.1f}%',(170+width,y),22)
text(d,'Unrealized gain by stock',(700,215),27,TEAL)
for i,row in enumerate(left.itertuples()):
    y=271+i*68
    text(d,row.ticker,(700,y),23)
    width=int(row.unrealized_gain/holdings.unrealized_gain.max()*245)
    d.rounded_rectangle((795,y,795+width,y+30),radius=5,fill=TEAL)
    text(d,f'{row.unrealized_gain:,.0f}',(805+width,y),22)
paragraph(d,'The app also includes sector allocation, largest-position concentration, and above/below-cost counts.',64,580,size=24)
save(im,'Allocation and gains',17,'Allocation charts show the share of selected portfolio value in each stock and sector. Gain and loss charts compare positions against purchase cost. The insights tab identifies the largest position and ranks gains relative to cost.')

im,d=base(7,'Price history: compare stock trends','06 / Historical analysis')
text(d,'First observation = 100  |  Synthetic closing prices',(64,213),23,MUTED)
box=(122,281,1200,544)
lo,hi=prices.indexed_price.min()-2,prices.indexed_price.max()+2
colors=[TEAL,BLUE,'#F4C56B','#D58AFF']
for val in [90,100,110,120]:
    if lo<=val<=hi:
        yy=box[3]-(val-lo)/(hi-lo)*(box[3]-box[1])
        d.line((box[0],yy,box[2],yy),fill=PANEL,width=2)
        text(d,str(val),(65,yy-12),20,MUTED)
for idx,(ticker,group) in enumerate(prices.groupby('ticker')):
    coords=[(box[0]+j/(len(group)-1)*(box[2]-box[0]),box[3]-(v-lo)/(hi-lo)*(box[3]-box[1])) for j,v in enumerate(group.indexed_price)]
    d.line(coords,fill=colors[idx],width=4)
    text(d,ticker,(130+idx*250,559),23,colors[idx])
text(d,'Jan 2025',(122,247),21,MUTED)
text(d,'Mar 2025',(1093,247),21,MUTED)
paragraph(d,'History mode provides closing-price charts, indexed growth, observed volatility, and drawdown.',64,600,size=22)
save(im,'Price-history chart',18,'Price-history mode displays stock closing prices and price growth indexed to one hundred. Users can choose tickers and a date range. It also calculates price change, volatility per observation, and maximum drawdown within that range.')

im,d=base(8,'How the calculations work','07 / Analysis logic')
items=[('Position value','Shares × uploaded current price'),('Unrealized gain','Position value − purchase cost'),('Observed volatility','Standard deviation of consecutive price changes'),('Maximum drawdown','Largest fall from an observed closing-price peak')]
for i,(label,formula) in enumerate(items):
    y=235+i*80
    text(d,label,(64,y),27,TEAL)
    paragraph(d,formula,420,y,width=790,size=27,color=TEXT)
paragraph(d,'Multiple lots use share-weighted purchase cost. Snapshot gains exclude dividends, fees, taxes, and sold positions.',64,580,size=24)
save(im,'Calculation methods',17,'Portfolio value is shares times current price. Unrealized gain is market value less purchase cost. Multiple purchase lots are combined using share-weighted cost. History volatility is measured per observation, without annualization. Drawdown tracks the decline from an observed price peak.')

im,d=base(9,'Python implementation and AI workflow','08 / Development')
for x,title,body in [(64,'Streamlit','Upload controls, column mapping, filters, dashboard tabs, and downloads.'),(459,'pandas','CSV loading, validation, grouped holdings, and historical calculations.'),(854,'Plotly','Interactive allocation, gain/loss, closing-price, and drawdown charts.')]:
    d.rounded_rectangle((x,230,x+362,461),radius=15,fill=PANEL)
    text(d,title,(x+22,257),30,TEAL)
    paragraph(d,body,x+22,319,width=318,size=24)
paragraph(d,'AI-assisted workflow: define a feature, generate code, review assumptions, and verify calculations.',64,506,size=29,color=TEXT)
paragraph(d,'The AI tab creates prompts locally; it does not call an AI service.',64,596,size=23)
save(im,'Implementation and AI assistance',18,'The interface uses Streamlit, data calculations use pandas, and charts use Plotly. AI assistance helped develop and refine the project. The built-in AI workflow produces local prompts for future improvements, while review and tests validate the resulting code.')

im,d=base(10,'Validation and current scope','09 / Project quality')
text(d,'13 automated tests passed',(64,228),36,TEAL)
paragraph(d,'Test coverage: weighted lots, gains, zero cost, invalid numbers, conflicting quotes, returns, drawdown, both app modes, mapping, and empty filters.',64,290,size=28)
d.rounded_rectangle((64,437,1216,606),radius=16,fill=PANEL)
text(d,'Current scope',(86,459),27,TEAL)
paragraph(d,'CSV-based prices, long stock holdings, and one currency per file. Historical stock charts do not infer portfolio returns without holdings and cash-flow history.',86,507,width=1080,size=25)
save(im,'Validation and limitations',17,'Thirteen automated tests validate the financial calculations and application behavior. Invalid data is reported rather than silently ignored. The project uses CSV prices, supports long stock positions, and uses one currency per file. Portfolio returns cannot be inferred from price history alone.')

im,d=base(11,'A working data application','10 / Conclusion')
paragraph(d,'Upload / Validate / Analyze / Visualize / Export',64,239,size=38,color=TEAL)
paragraph(d,'Delivered: a stock portfolio dashboard, downloadable sample datasets, interactive charts, validated calculations, and an AI-assisted development workflow.',64,331,size=30,color=TEXT)
paragraph(d,'Next improvements: live quotes, cash-flow-aware portfolio returns, and benchmark comparisons.',64,459,size=27)
text(d,'Presented by Ramadhar Mishra',(64,562),31,TEAL)
save(im,'Conclusion',13,'The result is a working stock data application that accepts uploads, validates inputs, analyzes holdings and prices, and exports results. Possible future extensions include live quotes, cash-flow-aware portfolio returns, and benchmark comparisons. Thank you.')

(OUT/'presentation_script.txt').write_text('Stock Portfolio Analyzer\nPresenter: Ramadhar Mishra\nCaptioned presentation; no audio track.\n\n'+'\n'.join(script))
concat=''.join(f"file '{path.as_posix()}'\nduration {duration}\n" for path,duration in slides)+f"file '{slides[-1][0].as_posix()}'\n"
(OUT/'slides.txt').write_text(concat)
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ffmpeg,'-y','-f','concat','-safe','0','-i',str(OUT/'slides.txt'),'-vf','fps=24,format=yuv420p','-c:v','libx264','-preset','fast','-crf','20','-movflags','+faststart','-t',str(sum(d for _,d in slides)),str(OUT/'Stock_Portfolio_Analyzer_Ramadhar_Mishra.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=(OUT/'encoding.log').open('w'))
print(f'Created {sum(d for _,d in slides)} second video: {OUT / "Stock_Portfolio_Analyzer_Ramadhar_Mishra.mp4"}')
