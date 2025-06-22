import type { CollectionConfig } from 'payload'
import { APIError } from 'payload'
import type { PayloadRequest } from 'payload'

export const Users: CollectionConfig = {
  slug: 'users',
  admin: {
    useAsTitle: 'email',
  },
  auth: {
    tokenExpiration: Number.isFinite(Number(process.env.TOKEN_EXPIRATION)) ? Number(process.env.TOKEN_EXPIRATION) : 604800, // 7 days in seconds
    maxLoginAttempts: Number.isFinite(Number(process.env.MAX_LOGIN_ATTEMPTS)) ? Number(process.env.MAX_LOGIN_ATTEMPTS) : 5,
  },
  // Removed global beforeLogin hook that blocked students entirely.
  // Admin UI access is still restricted via the `access.admin` rule below.

  access: {
    // Prevent students from accessing admin operations
    admin: ({ req }: { req: PayloadRequest }) => {
      const user = req.user
      return Boolean(user && user.role !== 'student')
    },
    create: ({ req }: { req: PayloadRequest }) => {
      const user = req.user
      return Boolean(user && (user.role === 'admin' || user.role === 'instructor'))
    },
    read: ({ req }: { req: PayloadRequest }) => {
      const user = req.user
      return Boolean(user && (user.role === 'admin' || user.role === 'instructor'))
    },
    update: ({ req }: { req: PayloadRequest }) => {
      const user = req.user
      return Boolean(user && (user.role === 'admin' || user.role === 'instructor'))
    },
    delete: ({ req }: { req: PayloadRequest }) => {
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
