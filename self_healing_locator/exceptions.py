class LocatorNotFoundError(Exception):
    """Raised when a named locator has no entry in the store and no selector to learn from."""


class HealingFailedError(Exception):
    """Raised when a broken locator could not be healed with sufficient confidence."""

    def __init__(self, name: str, old_selector: str, best_score: float, threshold: float):
        self.name = name
        self.old_selector = old_selector
        self.best_score = best_score
        self.threshold = threshold
        super().__init__(
            f"Could not heal locator '{name}' ({old_selector!r}): "
            f"best candidate scored {best_score:.2f}, below threshold {threshold:.2f}"
        )


class HealingRequiresReviewError(Exception):
    """Raised when the best healing candidate looks destructive (matches the
    risk deny-list) and was queued for human review instead of being
    auto-applied. See `Healer.store.list_pending()` / `shl review`.
    """

    def __init__(self, name: str, old_selector: str, new_selector: str, score: float):
        self.name = name
        self.old_selector = old_selector
        self.new_selector = new_selector
        self.score = score
        super().__init__(
            f"Locator '{name}' broke and the best replacement ({new_selector!r}, "
            f"confidence {score:.2f}) looks destructive -- queued for human review "
            f"instead of auto-applying. Run `shl review` to inspect it."
        )
