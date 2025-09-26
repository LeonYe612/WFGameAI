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

export interface CommonFields {
  team_id: number | null;
  created_at: string; // ISO 日期字符串
  creator_id: number;
  creator_name: string;
  updated_at: string; // ISO 日期字符串
  updater_id: number;
  updater_name: string;
  sort_order: number;
  lock_version: number;
  remark?: string | null;
}
