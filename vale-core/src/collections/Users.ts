import type { CollectionConfig } from 'payload'
import { APIError } from 'payload'

export const Users: CollectionConfig = {
  slug: 'users',
  admin: {
    useAsTitle: 'email',
  },
  auth: {
    maxLoginAttempts: 5,
  },
  hooks: {
    beforeLogin: [
      ({ req, user }) => {
        // Prevent students from logging into admin panel
        if (user && user.role === 'student') {
          throw new APIError(
            'Access Denied: Students cannot access the admin panel.',
            403,
            [
              {
                field: 'role',
                message: 'Student accounts are not authorized for admin access',
              },
            ],
            true
          )
        }
        return user
      }
    ]
  },
  access: {
    // Prevent students from accessing admin operations
    admin: ({ req }) => {
      const user = req.user
      return Boolean(user && user.role !== 'student')
    },
    create: ({ req }) => {
      const user = req.user
      return Boolean(user && (user.role === 'admin' || user.role === 'instructor'))
    },
    read: ({ req }) => {
      const user = req.user
      return Boolean(user && (user.role === 'admin' || user.role === 'instructor'))
    },
    update: ({ req }) => {
      const user = req.user
      return Boolean(user && (user.role === 'admin' || user.role === 'instructor'))
    },
    delete: ({ req }) => {
      const user = req.user
      return Boolean(user && user.role === 'admin') // Only admins can delete users
    },
  },
  fields: [
    // Email added by default
    {
      name: 'firstName',
      type: 'text',
      required: true,
      defaultValue: '',
    },
    {
      name: 'lastName',
      type: 'text',
      required: true,
      defaultValue: '',
    },
    {
      name: 'role',
      type: 'select',
      options: [
        { label: 'Student', value: 'student' },
        { label: 'Instructor', value: 'instructor' },
        { label: 'Admin', value: 'admin' },
      ],
      defaultValue: 'student',
    },
  ],
}
