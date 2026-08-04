import { reactive } from "vue";
import { isPhone } from "@pureadmin/utils";
import type { FormRules } from "element-plus";
import { $t, transformI18n } from "@/plugins/i18n";

/** 密码正则（密码格式应为8-18位数字、字母、符号的任意两种组合） */
export const REGEXP_PWD =
  /^(?![0-9]+$)(?![a-z]+$)(?![A-Z]+$)(?!([^(0-9a-zA-Z)]|[()])+$)(?!^.*[一-龥].*$)([^(0-9a-zA-Z)]|[()]|[a-z]|[A-Z]|[0-9]){8,18}$/;

/** 登录校验 */
const loginRules = reactive<FormRules>({
  password: [
    {
      validator: (_rule, value, callback) => {
        if (!value || value.length < 6) {
          callback(new Error("密码至少 6 个字符"));
        } else {
          callback();
        }
      },
      trigger: "blur"
    }
  ]
});

/** 忘记密码校验 */
const updateRules = reactive<FormRules>({
  phone: [
    {
      validator: (_rule, value, callback) => {
        if (value === "") {
          callback(new Error(transformI18n($t("login.purePhoneReg"))));
        } else if (!isPhone(value)) {
          callback(new Error(transformI18n($t("login.purePhoneCorrectReg"))));
        } else {
          callback();
        }
      },
      trigger: "blur"
    }
  ],
  verifyCode: [
    {
      validator: (_rule, value, callback) => {
        if (value === "") {
          callback(new Error(transformI18n($t("login.pureVerifyCodeReg"))));
        } else if (!REGEXP_PWD.test(value)) {
          callback(new Error(transformI18n($t("login.pureVerifyCodeSixReg"))));
        } else {
          callback();
        }
      },
      trigger: "blur"
    }
  ],
  password: [
    {
      validator: (_rule, value, callback) => {
        if (value === "") {
          callback(new Error(transformI18n($t("login.purePassWordReg"))));
        } else if (!REGEXP_PWD.test(value)) {
          callback(new Error(transformI18n($t("login.purePassWordRuleReg"))));
        } else {
          callback();
        }
      },
      trigger: "blur"
    }
  ]
});

export { loginRules, updateRules };
