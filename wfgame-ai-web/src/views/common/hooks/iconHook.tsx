import ManualIcon from "@/assets/svg/manual.svg?component";
import RecordIcon from "@/assets/svg/record.svg?component";

import FolderIcon from "@/assets/svg/folder.svg?component";
import FolderOpenIcon from "@/assets/svg/folder_open.svg?component";

import { scriptTypeEnum } from "@/utils/enums";

export const useIconHook = () => {
  const scriptTypeIcon = (type: any) => {
    const typeStr = String(type);
    switch (typeStr) {
      case String(scriptTypeEnum.RECORD.value):
        return <RecordIcon />;
      case String(scriptTypeEnum.MANUAL.value):
        return <ManualIcon />;
      default:
        return "";
    }
  };
  return { scriptTypeIcon };
};

export const folderIcon = (isOpen: boolean) => {
  return isOpen ? <FolderOpenIcon /> : <FolderIcon />;
};
