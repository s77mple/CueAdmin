// 公共类型 — 所有模块的 API 文件共用（框架层响应外壳，与具体业务无关）

/** 后端统一响应外壳 */
export type ApiResult<T = any> = {
  code: number;
  message: string;
  data: T;
};

/** 后端列表结构 — 所有列表接口统一用（分页接口按页返回，非分页接口 page=1、page_size=总数） */
export type PageData<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
};
