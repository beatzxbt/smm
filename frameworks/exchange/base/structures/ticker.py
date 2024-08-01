from typing import Dict

class Ticker:
    def __init__(
        self,
        fundingTime: float = None,
        fundingRate: float = None,
        markPrice: float = None,
        indexPrice: float = None,
    ) -> None:
        self._fundingTime = fundingTime
        self._fundingRate = fundingRate
        self._markPrice = markPrice
        self._indexPrice = indexPrice

    @property
    def fundingTime(self) -> float:
        return self._fundingTime

    @property
    def fundingRate(self) -> float:
        return self._fundingRate

    @property
    def markPrice(self) -> float:
        return self._markPrice

    @property
    def indexPrice(self) -> float:
        return self._indexPrice

    @property
    def fundingRateBps(self) -> float:
        return self._fundingRate * 10_000.0

    def __bool__(self) -> bool:
        return any(
            attr is not None
            for attr in [
                self._fundingTime,
                self._fundingRate,
                self._markPrice,
                self._indexPrice,
            ]
        )

    def __repr__(self) -> str:
        return (
            f"Ticker(fundingTime={self.fundingTime}, fundingRate={self.fundingRate}, "
            f"markPrice={self.markPrice}, indexPrice={self.indexPrice})"
        )

    def reset(self) -> None:
        """
        Resets all attributes of the Ticker object.
        """
        self._fundingTime = None
        self._fundingRate = None
        self._markPrice = None
        self._indexPrice = None

    def recordable(self) -> Dict[str, float]:
        """
        Unwraps the internal structures into widely-used Python structures
        for easy recordability (databases, logging, debugging etc). 

        Returns
        -------
        Dict
            A dict containing the current state of the orderbook.
        """
        return {
            "fundingTime": self.fundingTime,
            "fundingRate": self.fundingRate,
            "markPrice": self.markPrice,
            "indexPrice": self.indexPrice,
        }

    def update(
        self,
        fundingTime: float = None,
        fundingRate: float = None,
        markPrice: float = None,
        indexPrice: float = None,
    ) -> None:
        """
        Updates the attributes of the Ticker object with the provided values.

        Parameters
        ----------
        fundingTime : float, optional
            The funding timestamp to update.

        fundingRate : float, optional
            The funding rate to update.

        markPrice : float, optional
            The mark price to update.

        indexPrice : float, optional
            The index price to update.
        """
        if fundingTime is not None:
            self._fundingTime = fundingTime

        if fundingRate is not None:
            self._fundingRate = fundingRate

        if markPrice is not None:
            self._markPrice = markPrice

        if indexPrice is not None:
            self._indexPrice = indexPrice

    
