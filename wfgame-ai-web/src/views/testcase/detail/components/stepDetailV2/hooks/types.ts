/**
 * 菜单点击事件
 */
export type menuClickEvent = {
  menuLabel: string;
  currNode: any; // 触发右键菜单时激活的节点
};

// 自定义变量编辑器的单行数据
export type variable = {
  name: any;
  remark: any;
  location: any;
  value: any;
  type: any;
  key: any;
  treeNode: any; // 指向原始树节点的Ref对象
};
