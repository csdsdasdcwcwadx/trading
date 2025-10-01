import { useEffect } from 'react';
import './index.scss'

type ArbitrageParams = {
  exchange1Price: number; // 交易所1價格
  exchange1BuyFee: number; // 交易所1買入手續費
  exchange1SellFee: number; // 交易所1賣出手續費
  exchange2Price: number; // 交易所2價格
  exchange2BuyFee: number; // 交易所2買入手續費
  exchange2SellFee: number; // 交易所2賣出手續費
  amount: number; // 交易量（BTC 或其他幣種）
};

function calculateBidirectionalArbitrage(params: ArbitrageParams) {
  const { exchange1Price, exchange1BuyFee, exchange1SellFee,
          exchange2Price, exchange2BuyFee, exchange2SellFee, amount } = params;

  // 方向 A: Exchange1 買 -> Exchange2 賣
  const costA = exchange1Price * amount * (1 + exchange1BuyFee);
  const revenueA = exchange2Price * amount * (1 - exchange2SellFee);
  const profitA = revenueA - costA;

  // 方向 B: Exchange2 買 -> Exchange1 賣
  const costB = exchange2Price * amount * (1 + exchange2BuyFee);
  const revenueB = exchange1Price * amount * (1 - exchange1SellFee);
  const profitB = revenueB - costB;

  // 判斷哪個方向可行
  let bestDirection: string;
  if (profitA > 0 && profitB > 0) {
    bestDirection = profitA >= profitB ? "Exchange1買->Exchange2賣" : "Exchange2買->Exchange1賣";
  } else if (profitA > 0) {
    bestDirection = "Exchange1買->Exchange2賣";
  } else if (profitB > 0) {
    bestDirection = "Exchange2買->Exchange1賣";
  } else {
    bestDirection = "沒有可行套利方向";
  }

  return {
    profitA,
    profitB,
    bestDirection
  };
}


function App() {
  useEffect(() => {
    const result = calculateBidirectionalArbitrage({
      exchange1Price: 117028.37,  // Binance
      exchange1BuyFee: 0.0005,
      exchange1SellFee: 0.0005,
      exchange2Price: 116906.69,  // BitoPro
      exchange2BuyFee: 0.0005,
      exchange2SellFee: 0.0005,
      amount: 1
    });
    console.log(result)
  }, [])
  return (
    <>
      <div>
        123456
      </div>
    </>
  )
}

export default App
