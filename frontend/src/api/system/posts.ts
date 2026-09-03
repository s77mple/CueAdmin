import { http } from "@/utils/http";
import type { ApiResult, PageData } from "../types";
import type { Post, PostBrief } from "./types";

export const getPostList = (params?: object) =>
  http.get<ApiResult<PageData<Post>>>("/api/v1/system/posts", { params });
export const getPost = (id: number) =>
  http.get<ApiResult<Post>>(`/api/v1/system/posts/${id}`);
export const createPost = (data?: object) =>
  http.post<ApiResult<PostBrief>>("/api/v1/system/posts", { data });
export const updatePost = (id: number, data?: object) =>
  http.put<ApiResult<PostBrief>>(`/api/v1/system/posts/${id}`, { data });
export const deletePost = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/posts/${id}`);
