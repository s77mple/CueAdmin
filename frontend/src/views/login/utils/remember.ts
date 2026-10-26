/**
 * 「记住密码」的本地存储。
 *
 * ⚠️ 密码是**明文**存进 localStorage 的 —— 这只是免去每次手打的便利功能，
 * 挡不住能在这台电脑上打开开发者工具的人。所以默认**不勾选**，勾不勾由使用者自己决定；
 * 真正的登录凭证（token）另有自己的过期机制，不依赖这里。
 */
import { storageLocal } from "@pureadmin/utils";

const REMEMBER_KEY = "remember-login";

export interface RememberedLogin {
  username: string;
  password: string;
}

/** 读上次勾选「记住密码」时存下的账号；没存过、或存的数据坏了都返回 null。 */
export function getRememberedLogin(): RememberedLogin | null {
  try {
    const saved = storageLocal().getItem<Partial<RememberedLogin> | null>(
      REMEMBER_KEY
    );
    // 逐字段核对类型：存储可能被别的页面/版本写坏，宁可不回显也不要塞个 undefined 进表单
    if (
      typeof saved?.username !== "string" ||
      typeof saved?.password !== "string"
    ) {
      return null;
    }
    return { username: saved.username, password: saved.password };
  } catch {
    // localStorage 被禁用 / 内容不是合法 JSON —— 读取失败就当没存过
    return null;
  }
}

/** 勾选时存下，取消勾选时**清掉** —— 取消后不能还留着旧密码。 */
export function setRememberedLogin(value: RememberedLogin | null): void {
  try {
    if (value) {
      storageLocal().setItem(REMEMBER_KEY, value);
    } else {
      storageLocal().removeItem(REMEMBER_KEY);
    }
  } catch {
    // 隐私模式 / 配额满时写入会抛异常。这是便利功能，绝不能让它把
    // 「登录成功」顶成「登录失败」—— 调用点在登录成功的 .then 里。
  }
}
