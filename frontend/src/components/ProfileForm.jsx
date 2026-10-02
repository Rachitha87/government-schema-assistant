import { useEffect, useState } from 'react'

import api from '../api/client.js'
import { useProfile } from '../context/ProfileContext.jsx'

/**
 * The single "tell us about yourself" form.
 *
 * Deliberately short: five fields that the eligibility rules actually need,
 * plus a collapsed "more details" section. Every field is optional - whatever
 * is left blank simply limits how precisely we can check eligibility.
 */

const FALLBACK_STATES = [
  'Andhra Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Delhi', 'Goa', 'Gujarat', 'Haryana',
  'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra',
  'Odisha', 'Punjab', 'Rajasthan', 'Tamil Nadu', 'Telangana', 'Uttar Pradesh', 'Uttarakhand',
  'West Bengal',
]

const COURSES = ['B.Tech', 'B.Sc', 'B.Com', 'B.A', 'MCA', 'MBA', 'MA', 'M.Sc', 'M.Com', 'Diploma', 'ITI']

function Pick({ label, hint, children, optional }) {
  return (
    <label className="field">
      <span className="field-label">
        {label}
        {optional && <span className="field-hint">optional</span>}
        {hint && <span className="field-hint">{hint}</span>}
      </span>
      {children}
    </label>
  )
}

export default function ProfileForm({ onSubmit, submitting }) {
  const { profile, updateField, resetProfile } = useProfile()
  const [options, setOptions] = useState({
    states: FALLBACK_STATES,
    categories: ['General', 'OBC', 'EBC', 'SC', 'ST', 'DNT'],
    education_levels: ['Class 9-12', 'Class 11 and above', 'Diploma', 'Undergraduate', 'Postgraduate'],
  })

  useEffect(() => {
    api
      .getFilters()
      .then((data) => setOptions({ ...options, ...data }))
      .catch(() => {
        /* keep the built-in lists - the form still works */
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit()
  }

  const incomeChips = [100000, 200000, 300000, 500000, 800000]

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      <div className="profile-grid">
        <Pick label="Your age" hint="in years">
          <input
            type="number"
            min="5"
            max="100"
            inputMode="numeric"
            value={profile.age}
            onChange={(e) => updateField('age', e.target.value)}
            placeholder="19"
          />
        </Pick>

        <Pick label="Your state">
          <select value={profile.state} onChange={(e) => updateField('state', e.target.value)}>
            <option value="">Select your state</option>
            {options.states.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </select>
        </Pick>

        <Pick label="Category" hint="leave blank if unsure">
          <select
            value={profile.category}
            onChange={(e) => updateField('category', e.target.value)}
          >
            <option value="">Not sure yet</option>
            {options.categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </Pick>

        <Pick label="Family income per year" hint="in rupees, e.g. 200000">
          <input
            type="number"
            min="0"
            step="1000"
            inputMode="numeric"
            value={profile.family_income}
            onChange={(e) => updateField('family_income', e.target.value)}
            placeholder="200000"
          />
          <span className="quick-row">
            {incomeChips.map((amount) => (
              <button
                type="button"
                key={amount}
                className="quick-chip"
                onClick={() => updateField('family_income', amount)}
              >
                {`₹${amount / 100000} lakh`}
              </button>
            ))}
          </span>
        </Pick>

        <Pick label="What are you studying?">
          <select
            value={profile.education_level}
            onChange={(e) => updateField('education_level', e.target.value)}
          >
            <option value="">Select your level</option>
            {options.education_levels.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </Pick>

        <Pick label="Course or degree" hint="e.g. B.Tech, MCA">
          <input
            value={profile.course}
            onChange={(e) => updateField('course', e.target.value)}
            placeholder="B.Tech"
          />
          <span className="quick-row">
            {COURSES.map((course) => (
              <button
                type="button"
                key={course}
                className="quick-chip"
                onClick={() => updateField('course', course)}
              >
                {course}
              </button>
            ))}
          </span>
        </Pick>

        <Pick label="Gender" optional>
          <select value={profile.gender} onChange={(e) => updateField('gender', e.target.value)}>
            <option value="">Prefer not to say</option>
            <option value="Female">Female</option>
            <option value="Male">Male</option>
            <option value="Other">Other</option>
          </select>
        </Pick>

        <Pick label="Are you a full-time student?" optional>
          <select
            value={profile.student_status}
            onChange={(e) => updateField('student_status', e.target.value)}
          >
            <option value="">Prefer not to say</option>
            <option value="Full-time">Yes, full-time</option>
            <option value="Part-time">Part-time</option>
            <option value="Job/Working">No, I work</option>
            <option value="Unemployed">No, looking for work</option>
          </select>
        </Pick>
      </div>

      <details className="more-details">
        <summary>Add more details (optional)</summary>
        <div className="profile-grid">
          <Pick label="Your name" optional>
            <input
              value={profile.name}
              onChange={(e) => updateField('name', e.target.value)}
              placeholder="Ananya Sharma"
            />
          </Pick>
          <Pick label="Disability" optional>
            <select
              value={profile.disability_status}
              onChange={(e) => updateField('disability_status', e.target.value)}
            >
              <option value="">Prefer not to say</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </Pick>
          <Pick label="Last exam percentage" optional>
            <input
              type="number"
              min="0"
              max="100"
              value={profile.academic_percentage}
              onChange={(e) => updateField('academic_percentage', e.target.value)}
              placeholder="85"
            />
          </Pick>
        </div>
      </details>

      <div className="profile-actions">
        <button className="btn btn-lg btn-primary" type="submit" disabled={submitting}>
          {submitting ? 'Checking your eligibility…' : 'Show my schemes'}
        </button>
        <button
          type="button"
          className="btn btn-quiet"
          onClick={() => {
            resetProfile()
          }}
        >
          Clear
        </button>
      </div>
    </form>
  )
}