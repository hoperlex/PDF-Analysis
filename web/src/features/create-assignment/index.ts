/** Public API of the `create-assignment` feature (`W61-DISPATCHER-01`). */

export type { NewAssignment } from './model/use-create-assignment';
export { assignmentIntent, useCreateAssignment } from './model/use-create-assignment';
export type { CreateAssignmentFormProps, ExpertChoice } from './ui/create-assignment-form';
export { CreateAssignmentForm } from './ui/create-assignment-form';
