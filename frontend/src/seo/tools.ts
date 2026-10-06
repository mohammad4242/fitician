export const tools = [
  { kind: "calorie", path: "/tools/calorie-calculator", label: "کالری روزانه", title: "محاسبه کالری روزانه", symbol: "kcal", description: "تخمین کالری نگهدارنده و انرژی استراحت با توجه به شرایط و فعالیت تو." },
  { kind: "protein", path: "/tools/protein-calculator", label: "پروتئین روزانه", title: "محاسبه پروتئین روزانه", symbol: "g", description: "یک بازه آموزشی از پروتئین روزانه برای بزرگسال سالم و فعال." },
  { kind: "bmi", path: "/tools/bmi-calculator", label: "BMI", title: "محاسبه BMI؛ شاخص توده بدنی", symbol: "BMI", description: "نسبت وزن به قد، همراه با تفسیر محتاطانه و محدودیت‌های این شاخص." },
] as const;
export type ToolKind = typeof tools[number]["kind"];
