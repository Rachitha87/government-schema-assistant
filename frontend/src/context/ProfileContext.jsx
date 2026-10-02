/**
 * Profile context.
 *
 * The profile entered in the Profile page is remembered in the browser
 * (localStorage) and reused by the Chat and Browse pages, so the user does not
 * have to type the same details twice.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const STORAGE_KEY = 'gsa.profile'

const EMPTY_PROFILE = {
  name: '',
  age: '',
  gender: '',
  state: '',
  category: '',
  family_income: '',
  education_level: '',
  course: '',
  student_status: '',
  disability_status: '',
  disability_type: '',
  academic_percentage: '',
}

const ProfileContext = createContext(null)

function readStoredProfile() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? { ...EMPTY_PROFILE, ...JSON.parse(raw) } : EMPTY_PROFILE
  } catch {
    return EMPTY_PROFILE
  }
}

export function ProfileProvider({ children }) {
  const [profile, setProfile] = useState(readStoredProfile)

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
    } catch {
      /* private browsing - ignore */
    }
  }, [profile])

  const updateField = useCallback((field, value) => {
    setProfile((current) => ({ ...current, [field]: value }))
  }, [])

  const resetProfile = useCallback(() => setProfile(EMPTY_PROFILE), [])

  const isComplete = useMemo(
    () =>
      Boolean(
        profile.age &&
          profile.category &&
          profile.family_income &&
          profile.state &&
          profile.education_level,
      ),
    [profile],
  )

  /** Only send fields the user actually filled in. */
  const profilePayload = useCallback(() => {
    const payload = {}
    Object.entries(profile).forEach(([key, value]) => {
      if (value === '' || value == null) return
      if (key === 'age' || key === 'family_income' || key === 'academic_percentage') {
        payload[key] = Number(value)
      } else {
        payload[key] = value
      }
    })
    return payload
  }, [profile])

  const value = useMemo(
    () => ({ profile, updateField, resetProfile, isComplete, profilePayload }),
    [profile, updateField, resetProfile, isComplete, profilePayload],
  )

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>
}

export function useProfile() {
  const context = useContext(ProfileContext)
  if (!context) throw new Error('useProfile must be used inside <ProfileProvider>')
  return context
}

export { EMPTY_PROFILE }
