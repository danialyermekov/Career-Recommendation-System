import styles from './BrandLogo.module.css'

export default function BrandLogo() {
  const base = `${process.env.PUBLIC_URL || ''}/branding/careerflow-horizontal`
  return <picture className={styles.brand}>
    <source srcSet={`${base}.webp`} type="image/webp" />
    <img src={`${base}.png`} width="624" height="72" alt="CareerFlow" decoding="async" />
  </picture>
}
