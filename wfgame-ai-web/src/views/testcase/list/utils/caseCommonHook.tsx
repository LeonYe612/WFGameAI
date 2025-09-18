import CommonTestIcon from "@/assets/svg/common_test.svg?component";
import PressureTestIcon from "@/assets/svg/pressure_test.svg?component";
import RobotTestIcon from "@/assets/svg/robot_test.svg?component";
import BetTestIcon from "@/assets/svg/bet_test.svg?component";
import FireTestIcon from "@/assets/svg/fire_test.svg?component";
import OtherTestIcon from "@/assets/svg/other_test.svg?component";
import JMeterIcon from "@/assets/svg/jmeter.svg?component";
import { caseTypeEnum } from "@/utils/enums";

export const useCaseCommonHook = () => {
  const typeIconRender = (type: any) => {
    const typeStr = String(type);
    switch (typeStr) {
      case String(caseTypeEnum.COMMON.value):
        return <CommonTestIcon />;
      case String(caseTypeEnum.PRESSURE.value):
        return <PressureTestIcon />;
      case String(caseTypeEnum.ROBOT.value):
        return <RobotTestIcon />;
      case String(caseTypeEnum.BET.value):
        return <BetTestIcon />;
      case String(caseTypeEnum.FIRE.value):
        return <FireTestIcon />;
      case String(caseTypeEnum.OTHER.value):
        return <OtherTestIcon />;
      case String(caseTypeEnum.LOAD_TEST.value):
        return <JMeterIcon />;
      default:
        return "";
    }
  };
  return {
    typeIconRender
  };
};
