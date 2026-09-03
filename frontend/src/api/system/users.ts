import { http } from "@/utils/http";
import type { ApiResult, PageData } from "../types";
import type {
  User,
  UserListItem,
  UserCreate,
  UserUpdate,
  UserPatch,
  UserListQuery,
  UserDetail
} from "./types";

export const getUserList = (params?: UserListQuery) =>
  http.get<ApiResult<PageData<UserListItem>>>("/api/v1/system/users", {
    params
  });
export const getUser = (id: number) =>
  http.get<ApiResult<UserDetail>>(`/api/v1/system/users/${id}`);
export const createUser = (data: UserCreate) =>
  http.post<ApiResult<User>>("/api/v1/system/users", { data });
export const updateUser = (id: number, data: UserUpdate) =>
  http.put<ApiResult<User>>(`/api/v1/system/users/${id}`, { data });
export const patchUser = (id: number, data: UserPatch) =>
  http.patch<ApiResult<User>>(`/api/v1/system/users/${id}`, { data });
export const deleteUser = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/users/${id}`);
/** 彻底删除（仅限已禁用的用户） */
export const hardDeleteUser = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/users/${id}`, {
    params: { hard: true }
  });
