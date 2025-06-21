import type { CollectionConfig } from 'payload';

export const Enrollments: CollectionConfig = {
    slug: 'enrollments',
    admin: {
        useAsTitle: 'id',
    },
    fields: [
        {
            name: 'user',
            type: 'relationship',
            relationTo: 'users',
            required: true,
            label: 'User',
        },
        {
            name: 'course',
            type: 'relationship',
            relationTo: 'courses',
            required: true,
            label: 'Course',
        },
        {
            name: 'enrolledAt',
            type: 'date',
            required: true,
            defaultValue: () => new Date(),
            label: 'Enrolled At',
        },
        {
            name: 'status',
            type: 'select',
            options: [
                { label: 'Active', value: 'active' },
                { label: 'Completed', value: 'completed' },
                { label: 'Withdrawn', value: 'withdrawn' },
            ],
            defaultValue: 'active',
            required: true,
            label: 'Status',
        },
    ],
    timestamps: true,
};
