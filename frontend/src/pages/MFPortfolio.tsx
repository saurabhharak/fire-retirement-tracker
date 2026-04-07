import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { KiteConnectionBanner } from "../components/portfolio/KiteConnectionBanner";
import { PortfolioSummaryCards } from "../components/portfolio/PortfolioSummaryCards";
import { HoldingsTable } from "../components/portfolio/HoldingsTable";
import { ActiveSIPs } from "../components/portfolio/ActiveSIPs";
import { useKitePortfolio } from "../hooks/useKitePortfolio";

export default function MFPortfolio() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { status, statusLoading, portfolio, portfolioLoading, connect, disconnect, refresh } =
    useKitePortfolio();

  // Clear ?connected=true from URL after OAuth redirect
  useEffect(() => {
    if (searchParams.get("connected") === "true") {
      setSearchParams({}, { replace: true });
      refresh();
    }
  }, [searchParams, setSearchParams, refresh]);

  return (
    <div>
      <PageHeader title="MF Portfolio" subtitle="Live mutual fund holdings and SIPs from Zerodha Coin" />

      <KiteConnectionBanner
        status={status}
        isLoading={statusLoading}
        onConnect={connect}
        onDisconnect={disconnect}
        onRefresh={refresh}
        isStale={portfolio?.is_stale}
      />

      {status?.connected && (
        <>
          {portfolioLoading ? (
            <LoadingState message="Fetching portfolio from Zerodha..." />
          ) : portfolio ? (
            <>
              <PortfolioSummaryCards portfolio={portfolio} isLoading={false} />
              <HoldingsTable holdings={portfolio.holdings} />
              <ActiveSIPs sips={portfolio.sips} />
            </>
          ) : null}
        </>
      )}

      {!status?.connected && !statusLoading && (
        <div className="text-center py-16">
          <p className="text-[#E8ECF1]/40 text-lg mb-2">No portfolio data</p>
          <p className="text-[#E8ECF1]/30 text-sm">Connect your Zerodha account to see your MF holdings and SIPs</p>
        </div>
      )}
    </div>
  );
}
