import { Directive, type DirectiveBinding } from "vue";

export const focus: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const { value } = binding;
    if (value) {
      const inputElement = el.querySelector("input");
      if (inputElement) {
        (inputElement as HTMLInputElement).focus();
      }
    } else {
      throw new Error('need focus! Like v-focus="true"');
    }
  }
};
