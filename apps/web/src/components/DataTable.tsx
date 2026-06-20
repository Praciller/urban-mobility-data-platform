import type { ReactNode } from "react";

import { EmptyState } from "./StateBlocks";

export interface DataColumn<RowT> {
  header: string;
  render: (row: RowT) => ReactNode;
  align?: "left" | "right";
}

interface DataTableProps<RowT> {
  rows: RowT[];
  columns: DataColumn<RowT>[];
  getRowKey: (row: RowT) => string | number;
  emptyTitle: string;
  emptyDetail?: string;
}

export function DataTable<RowT>({
  rows,
  columns,
  getRowKey,
  emptyTitle,
  emptyDetail,
}: DataTableProps<RowT>) {
  if (rows.length === 0) {
    return <EmptyState title={emptyTitle} detail={emptyDetail} />;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th className={column.align === "right" ? "align-right" : undefined} key={column.header}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={getRowKey(row)}>
              {columns.map((column) => (
                <td className={column.align === "right" ? "align-right" : undefined} key={column.header}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
