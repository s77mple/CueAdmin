// 公共类型 — 所有 API 文件共用

/** 后端统一响应外壳 */
export type ApiResult<T = any> = {
  code: number;
  message: string;
  data: T;
};

/** 后端分页结构 */
export type PageData<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
};
