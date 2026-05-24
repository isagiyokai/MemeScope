from datetime import datetime, timezone, timedelta
from typing import Sequence, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.signal import Signal, SignalType
from schemas.signal_schema import SignalCreate
from repositories.signal_repo import SignalRepository
from repositories.holder_repo import HolderRepository
from repositories.trade_repo import TradeRepository
from repositories.token_repo import TokenRepository
from repositories.wallet_repo import WalletRepository
from services.signals.signal_publisher import publish_signal
from config.logging import get_logger

logger = get_logger(__name__)


class SignalEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.signal_repo = SignalRepository(session)
        self.holder_repo = HolderRepository(session)
        self.trade_repo = TradeRepository(session)
        self.token_repo = TokenRepository(session)
        self.wallet_repo = WalletRepository(session)

    async def evaluate_token(self, token_mint: str) -> list[Signal]:
        signals = []
        from services.signals.rules.smart_wallet_entry import SmartWalletEntryRule
        from services.signals.rules.top10_dump import Top10DumpRule
        from services.signals.rules.cluster_alert import ClusterAlertRule

        rules = [
            SmartWalletEntryRule(self.session),
            Top10DumpRule(self.session),
            ClusterAlertRule(self.session),
        ]

        for rule in rules:
            try:
                result = await rule.evaluate(token_mint)
                if result:
                    # Deduplication: skip if identical active signal exists recently
                    existing = await self.signal_repo.list_by_token(token_mint, active_only=True)
                    dup = any(
                        s.source_rule == result.source_rule and s.signal_type == result.signal_type
                        for s in existing
                    )
                    if not dup:
                        signal = await self.signal_repo.create(result)
                        await publish_signal(signal)
                        signals.append(signal)
                        logger.info("Signal generated", token=token_mint, rule=result.source_rule, type=result.signal_type)
            except Exception as e:
                logger.error("Rule evaluation failed", token=token_mint, rule=rule.__class__.__name__, error=str(e))

        return signals

    async def evaluate_all_tracked(self) -> list[Signal]:
        tokens = await self.token_repo.list_tracking()
        all_signals = []
        for token in tokens:
            sigs = await self.evaluate_token(token.mint_address)
            all_signals.extend(sigs)
        return all_signals
