-- Migration 010: Seed house construction expenses
-- IMPORTANT: Replace '544d7acc-476f-4f91-aefd-10124d52eb3b' with your actual Supabase user UUID
-- Find it at: Supabase Dashboard > Authentication > Users

BEGIN;

DO $$
DECLARE
    v_user_id uuid := '544d7acc-476f-4f91-aefd-10124d52eb3b';
    v_project_id uuid;
BEGIN
    -- Skip if project already exists
    SELECT id INTO v_project_id
    FROM public.projects
    WHERE user_id = v_user_id AND name = 'House Construction';

    IF v_project_id IS NOT NULL THEN
        RAISE NOTICE 'House Construction project already exists, skipping seed';
        RETURN;
    END IF;

    -- Create project
    INSERT INTO public.projects (user_id, name, status, start_date, end_date)
    VALUES (v_user_id, 'House Construction', 'completed', '2024-11-09', '2026-01-03')
    RETURNING id INTO v_project_id;

    -- Insert all 109 expenses (total_amount=0 becomes NULL)
    INSERT INTO public.project_expenses (project_id, date, category, description, total_amount, paid_amount, paid_by) VALUES
    (v_project_id, '2024-11-09', 'Architect & Structural Consulting', 'Advance payment', 50400, 10000, 'Saurabh Harak'),
    (v_project_id, '2024-12-16', 'RCC Contractor', 'Advance Payment', 659999.98, 15000, 'Saurabh Harak'),
    (v_project_id, '2024-12-24', 'RCC Contractor', '2nd installment', NULL, 15000, 'Saurabh Harak'),
    (v_project_id, '2024-12-25', 'Architect & Structural Consulting', '1st stage payment', NULL, 15000, 'Saurabh Harak'),
    (v_project_id, '2024-12-31', 'RCC Contractor', '3rd payment', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-01-06', 'Materials', '25MM and 40MM Cover block', 1000, 1000, 'Saurabh Harak'),
    (v_project_id, '2025-01-07', 'RCC Contractor', '4th payment', NULL, 40000, 'Saurabh Harak'),
    (v_project_id, '2025-01-14', 'RCC Contractor', '4th payment', NULL, 15000, 'Saurabh Harak'),
    (v_project_id, '2025-01-28', 'RCC Contractor', '5th payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-02-04', 'RCC Contractor', '6th payment', NULL, 50000, 'Saurabh Harak'),
    (v_project_id, '2025-02-11', 'RCC Contractor', '7th payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-02-17', 'RCC Contractor', '8th payment', NULL, 50000, 'Saurabh Harak'),
    (v_project_id, '2025-02-19', 'Electrical', 'Slab electricals', 4625, 4625, 'Saurabh Harak'),
    (v_project_id, '2025-02-23', 'Materials', 'Construction tape', 800, 800, 'Saurabh Harak'),
    (v_project_id, '2025-02-25', 'RCC Contractor', '9th payment', NULL, 40000, 'Saurabh Harak'),
    (v_project_id, '2025-02-28', 'Electrical', 'First slab electricals', 2885, 2885, 'Saurabh Harak'),
    (v_project_id, '2025-03-02', 'Electrical', 'Cable tie', 270, 0, 'Saurabh Harak'),
    (v_project_id, '2025-03-02', 'Electrical', 'Cable tie', NULL, 270, 'Saurabh Harak'),
    (v_project_id, '2025-03-03', 'RCC Contractor', '10th payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-03-04', 'RCC Contractor', '12th payment', NULL, 36000, 'Saurabh Harak'),
    (v_project_id, '2025-03-05', 'Architect & Structural Consulting', '1st slab payment', NULL, 15000, 'Saurabh Harak'),
    (v_project_id, '2025-03-11', 'RCC Contractor', '13th payment', NULL, 12000, 'Saurabh Harak'),
    (v_project_id, '2025-03-18', 'RCC Contractor', '13th payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-03-25', 'RCC Contractor', '15th payment', NULL, 50000, 'Saurabh Harak'),
    (v_project_id, '2025-03-31', 'Electrical', 'Second slab electricals', 2425, 2425, 'Saurabh Harak'),
    (v_project_id, '2025-03-31', 'Electrical', 'Electrician payment', 6000, 6000, 'Saurabh Harak'),
    (v_project_id, '2025-04-01', 'RCC Contractor', 'Payment', NULL, 50000, 'Saurabh Harak'),
    (v_project_id, '2025-04-02', 'RCC Contractor', 'Payment', NULL, 16000, 'Saurabh Harak'),
    (v_project_id, '2025-04-03', 'Electrical', '10 Pipes + Edge Fittings', 1280, 0, 'Saurabh Harak'),
    (v_project_id, '2025-04-08', 'RCC Contractor', 'Payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-04-15', 'RCC Contractor', 'Payment', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-04-22', 'RCC Contractor', 'Payment', NULL, 40000, 'Saurabh Harak'),
    (v_project_id, '2025-04-29', 'RCC Contractor', 'Payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-05-06', 'RCC Contractor', 'Payment', NULL, 35000, 'Saurabh Harak'),
    (v_project_id, '2025-05-13', 'RCC Contractor', 'Payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-05-21', 'Windows', 'Windows', 21305, 21305, 'Saurabh Harak'),
    (v_project_id, '2025-05-23', 'Electrical', 'Metal box for ground floor', 7800, 7800, 'Saurabh Harak'),
    (v_project_id, '2025-05-27', 'RCC Contractor', 'Payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-06-07', 'Flooring', 'Granite and transportation', 94001, 94001, 'Saurabh Harak'),
    (v_project_id, '2025-06-10', 'RCC Contractor', 'Payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-06-11', 'Windows', 'Window Craftsman - First payment', 8000, 8000, 'Saurabh Harak'),
    (v_project_id, '2025-06-11', 'Windows', 'Window grill paint', 580, 580, 'Saurabh Harak'),
    (v_project_id, '2025-06-24', 'RCC Contractor', 'Payment', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-07-16', 'Windows', 'Steel', 25148, 25148, 'Saurabh Harak'),
    (v_project_id, '2025-07-16', 'Windows', 'Grill labour charges', 7000, 7000, 'Saurabh Harak'),
    (v_project_id, '2025-07-20', 'Electrical', 'Remaining materials', NULL, 2716, 'Saurabh Harak'),
    (v_project_id, '2025-07-21', 'Windows', 'Window Steel Frame', 9630, 9630, 'Saurabh Harak'),
    (v_project_id, '2025-07-21', 'Transport', 'Grill Steel Transport (Vehicle Rent)', 500, 500, 'Saurabh Harak'),
    (v_project_id, '2025-07-24', 'Materials', 'Chicken mesh', 1330, 1330, 'Saurabh Harak'),
    (v_project_id, '2025-07-24', 'Electrical', 'Electrician (Barkale) Labour', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-07-24', 'Flooring', 'Window grill labour', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-07-29', 'RCC Contractor', 'Payment', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-07-31', 'Windows', 'Granite window frame labour payment', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-08-05', 'RCC Contractor', 'Plaster payment 1', NULL, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-08-12', 'RCC Contractor', 'Plaster payment 2', NULL, 25000, 'Saurabh Harak'),
    (v_project_id, '2025-08-19', 'RCC Contractor', 'Payment', NULL, 25000, 'Saurabh Harak'),
    (v_project_id, '2025-08-26', 'RCC Contractor', 'Payment', NULL, 25000, 'Saurabh Harak'),
    (v_project_id, '2025-08-26', 'Plumbing', 'Water tank advance', 35000, 5000, 'Saurabh Harak'),
    (v_project_id, '2025-08-26', 'Plumbing', 'Diverter and flush valve', NULL, 31172, 'Saurabh Harak'),
    (v_project_id, '2025-08-27', 'Architect & Structural Consulting', 'Payment', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-08-30', 'Flooring', 'Advance payment', 11111, 11111, 'Saurabh Harak'),
    (v_project_id, '2025-09-03', 'Flooring', 'Remaining payment', 77969, 77969, 'Saurabh Harak'),
    (v_project_id, '2025-09-04', 'Plumbing', 'Morya Hardware Store', 1740, 1740, 'Saurabh Harak'),
    (v_project_id, '2025-09-09', 'RCC Contractor', 'Brick Waterproofing (Coba)', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-09-13', 'Plumbing', 'Ankush Plumber - Payment', 5000, 5000, 'Saurabh Harak'),
    (v_project_id, '2025-09-15', 'Flooring', 'Ram Bhai - Tile Labour', 15000, 15000, 'Saurabh Harak'),
    (v_project_id, '2025-09-15', 'Plumbing', 'Toilet seat', 9889, 9889, 'Saurabh Harak'),
    (v_project_id, '2025-09-16', 'RCC Contractor', 'Brick Waterproofing (Coba)', NULL, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-09-21', 'Plumbing', 'Darshan Plumber - 1st Payment', 24000, 24000, 'Saurabh Harak'),
    (v_project_id, '2025-09-21', 'Plumbing', 'Darshan Plumber - 2nd Payment', 45000, 45000, 'Saurabh Harak'),
    (v_project_id, '2025-09-21', 'Plumbing', 'Wash basin and kitchen sink', 9264, 9264, 'Saurabh Harak'),
    (v_project_id, '2025-10-06', 'Flooring', 'Flooring labour payment', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-10-07', 'RCC Contractor', 'Brick Bed Waterproofing (Coba) final payment', NULL, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-10-10', 'Flooring', 'Tiles purchase', 58655, 58655, 'Saurabh Harak'),
    (v_project_id, '2025-10-11', 'Flooring', 'Labour payment', 20000, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-10-13', 'Electrical', 'Wire', 65945, 65945, 'Saurabh Harak'),
    (v_project_id, '2025-10-13', 'Interior', 'POP (Plaster of Paris)', 30000, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-10-16', 'Flooring', 'Labour payment', 30000, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-10-18', 'Electrical', 'Labour payment', 20000, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-10-28', 'Flooring', 'Labour payment', 20000, 20000, 'Saurabh Harak'),
    (v_project_id, '2025-10-28', 'Flooring', 'Granite and porch tiles', 13000, 13000, 'Saurabh Harak'),
    (v_project_id, '2025-11-05', 'Doors & Frames', 'Advance', 156104, 88000, 'Saurabh Harak'),
    (v_project_id, '2025-11-05', 'Windows', 'Advance', 130000, 5000, 'Saurabh Harak'),
    (v_project_id, '2025-11-05', 'Interior', 'POP Bags + Labour Petrol Expense', 350, 350, 'Saurabh Harak'),
    (v_project_id, '2025-11-06', 'Flooring', 'POP (Plaster of Paris)', 15000, 15000, 'Saurabh Harak'),
    (v_project_id, '2025-11-06', 'Interior', 'Gypsum labour payment', 1300, 1300, 'Saurabh Harak'),
    (v_project_id, '2025-11-06', 'Windows', 'First payment', NULL, 62000, 'Saurabh Harak'),
    (v_project_id, '2025-11-07', 'Flooring', 'Tiles labour payment', 40000, 40000, 'Saurabh Harak'),
    (v_project_id, '2025-11-11', 'Doors & Frames', 'Final payment done which was 156104', NULL, 68000, 'Saurabh Harak'),
    (v_project_id, '2025-11-11', 'Transport', 'Door transportation', 1200, 1200, 'Saurabh Harak'),
    (v_project_id, '2025-11-16', 'Flooring', 'Tiles labour payment', 30000, 30000, 'Saurabh Harak'),
    (v_project_id, '2025-11-16', 'Electrical', 'Switch and socket', 39751, 39751, 'Saurabh Harak'),
    (v_project_id, '2025-11-16', 'Flooring', 'Acid wash items', 680, 680, 'Saurabh Harak'),
    (v_project_id, '2025-11-30', 'Plumbing', 'Tap and shower and other items', NULL, 9895, 'Saurabh Harak'),
    (v_project_id, '2025-11-30', 'Electrical', 'Geyser and home made geyser items', 3565, 3565, 'Saurabh Harak'),
    (v_project_id, '2025-11-30', 'Electrical', 'Geyser and home made geyser items', 1001, 1001, 'Saurabh Harak'),
    (v_project_id, '2025-11-30', 'Plumbing', 'Jaguar fittings', NULL, 7754, 'Saurabh Harak'),
    (v_project_id, '2025-12-01', 'Flooring', 'Tiles labour payment', 4178, 4178, 'Saurabh Harak'),
    (v_project_id, '2025-12-04', 'Interior', 'POP payment', 5000, 5000, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Interior', 'Paint payment', 10000, 10000, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Interior', 'Paint labour', 11000, 11000, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Electrical', 'Electrical plates and dimmer', 10304, 10304, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Electrical', 'Lights', 24535, 24535, 'Saurabh Harak'),
    (v_project_id, '2025-12-23', 'Doors & Frames', 'Main door', 38850, 38850, 'Saurabh Harak'),
    (v_project_id, '2026-01-01', 'Doors & Frames', 'Main door accessories', 2000, 2000, 'Saurabh Harak'),
    (v_project_id, '2026-01-01', 'Doors & Frames', 'Main door labour payment', 3689, 3689, 'Saurabh Harak'),
    (v_project_id, '2026-01-01', 'Plumbing', 'Sewage tank labour payment', 7400, 7400, 'Saurabh Harak'),
    (v_project_id, '2026-01-03', 'Interior', 'Paint material payment', 15000, 15000, 'Saurabh Harak'),
    (v_project_id, '2026-01-03', 'Electrical', 'Labour payment', 10000, 10000, 'Saurabh Harak');

END $$;

COMMIT;
