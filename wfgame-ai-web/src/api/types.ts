export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface CommonQuery {
  id?: string | number;
  page?: number;
  page_size?: number;
  keyword?: string;
}
