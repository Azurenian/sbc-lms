import type { CollectionConfig } from 'payload';

export const Courses: CollectionConfig = {
    slug: 'courses',
    admin: {
        useAsTitle: 'title',
    },
    fields: [
        {
            name: 'title',
            type: 'text',
            required: true,
        },
        {
            name: 'description',
            type: 'textarea',
            required: true,
        },
        {
            name: 'instructor',
            type: 'relationship',
            relationTo: 'users',
            required: true,
        },
        {
            name: 'startDate',
            type: 'date',
            required: true,
        },
        {
            name: 'endDate',
            type: 'date',
            required: false,
        },
        {
            name: 'published',
            type: 'checkbox',
            defaultValue: false,
        },
        {
            name: 'image',
            type: 'upload',
            relationTo: 'media',
            required: false,
        },
    ],
};

