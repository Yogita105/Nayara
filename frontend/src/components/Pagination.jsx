import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./ui/button";

/**
 * Move between pages and say where the current one sits, so it is clear that
 * records exist beyond the ones on screen.
 */
export default function Pagination({
  page,
  pageSize,
  pageCount,
  total,
  onPageChange,
  noun = "records",
}) {
  if (total === 0) return null;

  const first = page * pageSize + 1;
  const last = Math.min(total, (page + 1) * pageSize);
  const onlyPage = pageCount <= 1;

  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 mt-5"
      data-testid="pagination"
    >
      <p className="text-sm text-[#64748B]" data-testid="pagination-summary">
        Showing <span className="font-medium text-[#0F172A]">{first}</span>–
        <span className="font-medium text-[#0F172A]">{last}</span> of{" "}
        <span className="font-medium text-[#0F172A]">{total}</span> {noun}
      </p>

      {!onlyPage && (
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="rounded-full"
            onClick={() => onPageChange(page - 1)}
            disabled={page === 0}
            data-testid="pagination-previous"
          >
            <ChevronLeft className="w-4 h-4 mr-1" aria-hidden="true" /> Previous
          </Button>
          <span className="text-sm text-[#64748B]" data-testid="pagination-position">
            Page {page + 1} of {pageCount}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="rounded-full"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pageCount - 1}
            data-testid="pagination-next"
          >
            Next <ChevronRight className="w-4 h-4 ml-1" aria-hidden="true" />
          </Button>
        </div>
      )}
    </div>
  );
}
