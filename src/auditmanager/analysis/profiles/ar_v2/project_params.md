<!-- legacy_path: prompts/disciplines/AR/project_params.md -->
<!-- legacy_sha256: 5d827feac80cf85760af4a1d3f8509e15defb0df771c09ea83e475e172a80f35 -->
<!-- reviewed_lines: 2-11 and 15-33 field vocabulary only; 13-35 sample values and 37-58 examples excluded as defaults -->

<!-- prompt:start -->
Имена полей помогают узнать, что два текста описывают один и тот же признак:
building_floors, building_height_m, building_class, fire_resistance_degree,
structural_fire_hazard_class, structural_system, climate_zone, wind_region,
snow_region, energy_class, apartment_count, total_area_m2, living_area_m2,
wall_construction, insulation_material, insulation_thickness_mm, facade_type,
roof_type, mgn_apartments_count.
Значение извлекай только из дословно указанного текста проекта; пустое или
неупомянутое поле не становится нулём и не является находкой. Сравнивай
значения только для одного объекта и одной характеристики. Нормативную
ссылку можно цитировать как утверждение проекта, но нельзя подтверждать
её актуальность из этого списка.
<!-- prompt:end -->

Review: all 19 field names are vocabulary. The sample zero/empty values,
building-class example and illustrated values in legacy lines 15-58 are not
product defaults, evidence of absence or a compliance decision.
