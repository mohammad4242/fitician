from app.exercises.enums import BodyRegion, MuscleGroup

BODY_REGION_CATEGORIES = (
    (BodyRegion.UPPER_BODY, "Upper Body", "بالاتنه"),
    (BodyRegion.LOWER_BODY, "Lower Body", "پایین‌تنه"),
    (BodyRegion.CORE, "Core", "میان‌تنه"),
)
UPPER_BODY_CATEGORIES = (
    (MuscleGroup.CHEST, "Chest", "سینه"),
    (MuscleGroup.BACK, "Back", "پشت و زیر بغل"),
    (MuscleGroup.SHOULDERS, "Shoulders", "سرشانه"),
    (MuscleGroup.BICEPS, "Biceps", "جلو بازو"),
    (MuscleGroup.TRICEPS, "Triceps", "پشت بازو"),
    (MuscleGroup.TRAPS, "Traps", "کول"),
    (MuscleGroup.FOREARMS, "Forearms", "ساعد"),
    (MuscleGroup.NECK, "Neck", "گردن"),
)
LOWER_BODY_CATEGORIES = (
    (MuscleGroup.GLUTES, "Glutes", "باسن"),
    (MuscleGroup.QUADRICEPS, "Quadriceps", "جلو پا"),
    (MuscleGroup.HAMSTRINGS, "Hamstrings", "پشت پا"),
    (MuscleGroup.ADDUCTORS, "Adductors", "داخل پا"),
    (MuscleGroup.ABDUCTORS, "Abductors", "بیرون پا"),
    (MuscleGroup.LEGS, "Legs", "کل پا"),
    (MuscleGroup.CALVES, "Calves", "ساق"),
)
CORE_CATEGORIES = (
    (MuscleGroup.ABS, "Abs", "شکم"),
    (MuscleGroup.OBLIQUES, "Obliques", "پهلو"),
)

