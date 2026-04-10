from src.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)


class ReportReasonNotFoundError(NotFoundError):
    detail = "Report reason not found"


class ListingReportNotFoundError(NotFoundError):
    detail = "Report not found"


class DuplicateReportReasonSlugError(ConflictError):
    detail = "Report reason slug already exists"


class ReservedOtherReasonSlugError(ConflictError):
    detail = "The 'other' report reason is reserved"


class OtherReasonCannotBeDeactivatedError(BadRequestError):
    detail = "The 'other' report reason cannot be deactivated"


class ReportReasonInactiveError(BadRequestError):
    detail = "Report reason is not available"


class CustomReasonDetailsRequiredError(BadRequestError):
    detail = "Additional information is required for the 'other' reason"


class CannotReportOwnListingError(ForbiddenError):
    detail = "You cannot report your own listing"


class DuplicatePendingListingReportError(ConflictError):
    detail = "You already have a pending report for this listing"


class ListingReportAlreadyResolvedError(ConflictError):
    detail = "Report has already been resolved"
